"""Run the terminal scene benchmark through the signed-in Codex CLI."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
from statistics import median
import struct
import subprocess
import tempfile
from time import perf_counter
import zlib

from demo import scene_frame
from generate_scene import codex_command, codex_environment, scene_response_text
from scene import HEIGHT, WIDTH, PlayState, parse_scene

HERE = Path(__file__).resolve().parent
MODELS = (
    "gpt-6.1-sol", "gpt-6-astra", "gpt-6.1-terra", "gpt-6-sol",
    "gpt-6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
)
CASES = {
    "forest": (("Trail sign", "Lookout blind", "White bear"), (3, 1, 2, 3, 3)),
    "house": (("Cat", "Toy basket", "Dog"), (3, 1, 2, 3, 1, 3)),
    "map": ((), ()),
    "elf": (("Elf gatekeeper", "Moonfire brazier", "Rune arch"), (3, 1, 2, 3, 2, 3)),
    "starry-night": ((), ()),
}
COUNTERS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
LAND = (214, 211, 165)
OCEAN = (41, 75, 101)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_prompts(path):
    blocks = re.findall(r"^```text\n(.*?)^\x60\x60\x60$", path.read_text(encoding="utf-8"), re.M | re.S)
    shared, *cases = blocks
    return {name: shared + "\n" + prompt for name, prompt in zip(CASES, cases, strict=True)}


def read_events(path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event


def read_usage(events):
    turns = [
        event["usage"] for event in events
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict)
    ]
    return {
        name: sum(turn[name] for turn in turns)
        if turns and all(type(turn.get(name)) is int for turn in turns) else None
        for name in COUNTERS
    }


def api_estimate(usage, rates):
    """Apply short-context standard rates to the reported token categories."""
    input_tokens, cached, output, _ = (usage[key] for key in COUNTERS)
    if rates is None or None in (input_tokens, cached, output):
        return None
    if not 0 <= cached <= input_tokens <= 272_000 or output < 0:
        return None
    return round(
        ((input_tokens - cached) * rates["input"] + cached * rates["cached_input"]
         + output * rates["output"]) / 1_000_000,
        9,
    )


def write_png(path, pixels, scale):
    height, width = len(pixels), len(pixels[0])

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    lines = [b"\0" + b"".join(bytes(pixel) * scale for pixel in row) for row in pixels]
    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    compressed = zlib.compress(b"".join(line * scale for line in lines))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
        + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    )


def render_result(directory, case, scene, land_reference):
    names, presses = CASES[case]
    state = PlayState(scene)

    def save_frame(label):
        pixels = scene_frame(state, WIDTH, HEIGHT // 2, 0)
        write_png(directory / (label + ".png"), pixels, 1)
        write_png(directory / (label + "-4x.png"), pixels, 4)

    save_frame("00-initial")
    if not presses:
        if case == "map":
            viewport = [pixel for row in state.pixels(0)[4:76] for pixel in row]
            land = bytes(pixel == LAND for pixel in viewport)
            (directory / "land-mask.bin").write_bytes(land)
            score = {"uses_required_colors": set(viewport) == {LAND, OCEAN}}
            if land_reference is not None:
                pairs = list(zip(land, land_reference, strict=True))
                union = sum(bool(pred or reference) for pred, reference in pairs)
                score["land_iou"] = sum(pred and reference for pred, reference in pairs) / union if union else None
                colors = {(0, 0): OCEAN, (1, 1): LAND, (1, 0): (224, 145, 72), (0, 1): (210, 102, 136)}
                difference = [colors[pair] for pair in pairs]
                write_png(directory / "land-difference.png", [
                    difference[start:start + WIDTH] for start in range(0, len(difference), WIDTH)
                ], 4)
            else:
                score["land_iou"] = None
        else:
            frame = state.pixels(0)
            score = {"uniform_side_matte": len({pixel for row in frame for pixel in row[:22] + row[122:]}) == 1}
        return score

    steps = []
    for step, key in enumerate(presses, 1):
        target = scene.targets[key - 1]
        before = state.pixels(0)
        used = state.used.copy()
        state.interact(key - 1)
        save_frame(f"{step:02d}-key-{key}")
        steps.append({
            "key": key, "target": target.name, "dialogue": state.dialogue,
            "art_changed": before != state.pixels(0),
            "newly_used": sorted(state.used - used),
            "uses_revisit_text": bool(target.revisit and target.name in used and state.dialogue == target.revisit),
        })
    checks = {
        "matches_object_order": tuple(target.name.casefold() for target in scene.targets) == tuple(
            name.casefold() for name in names
        ),
        "first_action_is_blocked": not steps[0]["art_changed"] and not steps[0]["newly_used"],
        "prerequisite_changes_art": steps[2]["art_changed"],
        "dependent_action_changes_art": steps[3]["art_changed"],
        "repeat_actions_preserve_art_and_report_state": all(
            not step["art_changed"] and not step["newly_used"] and step["uses_revisit_text"]
            for step in steps[4:]
        ),
        "steps": steps,
    }
    if case == "house":
        checks["cat_changes_art"] = steps[1]["art_changed"]
    return checks


def run_attempt(directory, request, model, case, timeout, rates, land_reference):
    directory.mkdir()
    output = directory / "response.txt"
    event_path = directory / "events.jsonl"
    error_path = directory / "stderr.log"
    command = codex_command(output, model, medium=True)
    (directory / "request.txt").write_text(request, encoding="utf-8")
    write_json(directory / "command.json", command)

    error = None
    scene = None
    started = perf_counter()
    with tempfile.TemporaryDirectory(prefix="terminal-scene-eval-") as cwd:
        with event_path.open("w") as event_log, error_path.open("w") as error_log:
            try:
                result = subprocess.run(
                    command, input=request, encoding="utf-8", cwd=cwd, env=codex_environment(),
                    stdout=event_log, stderr=error_log, timeout=timeout,
                )
                if result.returncode:
                    error = next(
                        (line for line in reversed(error_path.read_text(errors="replace").splitlines())
                         if line.startswith("Error:")),
                        f"Codex exited with status {result.returncode}",
                    )
            except subprocess.TimeoutExpired:
                error = f"Codex timed out after {timeout} seconds"
            except OSError as exc:
                error = str(exc)

    status = "cli-failed" if error else "invalid"
    raw = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
    if not error:
        try:
            data = json.loads(scene_response_text(raw))
            if not isinstance(data, dict) or data.get("version") != 2:
                raise ValueError("expected a version 2 scene JSON object")
            write_json(directory / "parsed.json", data)
            names, _ = CASES[case]
            scene = parse_scene(data, allow_static=not names)
            if len(scene.targets) != len(names):
                raise ValueError(f"expected exactly {len(names)} interactable objects")
            status = "valid"
        except ValueError as exc:
            scene = None
            error = str(exc)

    wall_seconds = round(perf_counter() - started, 3)
    events = list(read_events(event_path))
    usage = read_usage(events)
    observed_models = sorted({event["model"] for event in events if isinstance(event.get("model"), str)})
    capture = {
        "status": status, "error": error, "generation_and_validation_seconds": wall_seconds,
        "reported_model_ids": observed_models, **usage,
        "api_equivalent_usd": None if any(name != model for name in observed_models) else api_estimate(usage, rates),
        "subscription_credits": None,
    }
    if scene is not None:
        render_start = perf_counter()
        write_json(directory / "checks.json", render_result(directory, case, scene, land_reference))
        capture["render_seconds"] = round(perf_counter() - render_start, 3)
    write_json(directory / "metrics.json", capture)
    return capture, raw


def run_trial(root, model, case, trial, prompt, running_order, args, rates, land_reference):
    directory = root / model / case / f"trial-{trial:02d}"
    directory.mkdir(parents=True)
    first, raw = run_attempt(directory / "attempt-1", prompt, model, case, args.timeout, rates, land_reference)
    attempts = [first]
    if first["status"] == "invalid" and raw.strip():
        retry_prompt = (
            f"{prompt}\n\nYour previous response follows. Return a complete corrected scene JSON object.\n"
            f"Validator error: {first['error']}\n\n{raw}"
        )
        repair, _ = run_attempt(
            directory / "attempt-2", retry_prompt, model, case, args.timeout, rates, land_reference,
        )
        attempts.append(repair)

    combined_fields = (*COUNTERS, "api_equivalent_usd")
    totals = {
        field: round(sum(attempt[field] for attempt in attempts), 9)
        if all(attempt[field] is not None for attempt in attempts) else None
        for field in combined_fields
    }
    row = {
        "model": model, "case": case, "trial": trial, "order": running_order,
        "reasoning_effort": "medium", "attempts": len(attempts),
        "first_status": first["status"], "final_status": attempts[-1]["status"],
        "first_seconds": first["generation_and_validation_seconds"],
        "total_seconds": round(sum(attempt["generation_and_validation_seconds"] for attempt in attempts), 3),
        **totals, "subscription_credits": None, "error": attempts[-1]["error"],
    }
    write_json(directory / "trial.json", row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", choices=MODELS, help="repeat to test a subset")
    parser.add_argument("--case", action="append", choices=CASES, help="repeat to test a subset")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--timeout", type=int, default=180, help="seconds per attempt")
    parser.add_argument("--out", type=Path, help="new results directory")
    parser.add_argument("--land-reference", type=Path, help="optional 144 x 72 row-major byte mask (0 water, 1 land)")
    args = parser.parse_args()
    if args.trials < 1 or args.timeout < 1:
        parser.error("--trials and --timeout must be positive")
    if not shutil.which("codex"):
        parser.error("codex is missing from PATH")
    models = list(dict.fromkeys(args.model or MODELS))
    cases = list(dict.fromkeys(args.case or CASES))
    catalog = json.loads((HERE / "api-rates.json").read_text(encoding="utf-8"))
    land_reference = args.land_reference.read_bytes() if args.land_reference else None
    if land_reference is not None and (len(land_reference) != WIDTH * 72 or set(land_reference) != {0, 1}):
        parser.error("--land-reference must contain 144 x 72 bytes of binary land and ocean values")
    started = datetime.now(timezone.utc)
    root = (args.out or HERE / "results" / started.strftime("%Y%m%dT%H%M%S.%fZ")).resolve()
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("choose a new results directory")
    prompts = read_prompts(HERE / "prompts.md")
    cli = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=10)
    sources = (Path(__file__).resolve(), HERE / "prompts.md", HERE / "api-rates.json",
               HERE.parent / "generate_scene.py", HERE.parent / "scene.py", HERE.parent / "demo.py",
               HERE.parent / "terminal_renderer.py")
    write_json(root / "run.json", {
        "utc_start": started.isoformat(), "cli_version": cli.stdout.strip(),
        "models": models, "cases": cases, "trials": args.trials, "seed": args.seed,
        "reasoning_effort": "medium", "service_tier": "CLI default with user config disabled",
        "timeout_seconds": args.timeout, "api_rates": catalog,
        "source_hashes": {str(path.relative_to(HERE.parent)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    })
    if land_reference is not None:
        (root / "land-reference.bin").write_bytes(land_reference)

    randomizer = random.Random(args.seed)
    rows = []
    for trial in range(1, args.trials + 1):
        schedule = [(model, case) for model in models for case in cases]
        randomizer.shuffle(schedule)
        for model, case in schedule:
            print(f"Trial {trial} · {model} · {case}", flush=True)
            row = run_trial(
                root, model, case, trial, prompts[case], len(rows) + 1, args,
                catalog["models"].get(model), land_reference,
            )
            rows.append(row)
            csv_path = root / "summary.csv"
            with csv_path.open("a", newline="", encoding="utf-8") as summary:
                writer = csv.DictWriter(summary, fieldnames=row.keys())
                if len(rows) == 1:
                    writer.writeheader()
                writer.writerow(row)
            print(f"  {row['final_status']} in {row['total_seconds']:.3f}s", flush=True)

    aggregates = []
    for model in models:
        for case in cases:
            group = [row for row in rows if row["model"] == model and row["case"] == case]
            times = [row["total_seconds"] for row in group if row["final_status"] == "valid"]
            aggregates.append({
                "model": model, "case": case, "trials": len(group),
                "first_pass_valid": sum(row["first_status"] == "valid" for row in group),
                "final_valid": len(times), "median_valid_seconds": median(times) if times else None,
                "valid_seconds_range": [min(times), max(times)] if times else None,
            })
    write_json(root / "aggregates.json", aggregates)
    valid = sum(row["final_status"] == "valid" for row in rows)
    print(f"Saved {len(rows)} trials ({valid} valid) to {root}")
    return 0 if valid == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
