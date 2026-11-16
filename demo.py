"""Run the tavern or a prompt-generated scene in a truecolor terminal."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
import sys
import termios
import textwrap
import time
import tty

from scene import PlayState, Scene, Target, load_indexed_frame
from terminal_renderer import RESET, RGB, encode_frame

EXAMPLES = Path(__file__).resolve().parent / "examples"
FRAME_INTERVAL = 0.45
SIZE_INTERVAL = 0.10


def tavern() -> Scene:
    return Scene(
        "The Lighthouse Tavern",
        "You came from the lighthouse? Sit down. Someone has been waiting for you to open that letter.",
        load_indexed_frame(EXAMPLES / "tavern.txt"),
        (
            Target("Wet letter", (55, 61, 14, 9),
                   "The ink has run, but the wax is intact. The seal shows an upside-down lighthouse."),
            Target("Innkeeper", (77, 30, 19, 22),
                   "Keep your voice down. Someone has been waiting beyond the back door."),
            Target("Back door", (108, 24, 27, 33),
                   "A cold draft slips through the gap. You hear two short knocks."),
        ),
        (
            (24, 62, 64, (246, 195, 126)),
            (25, 61, 65, (255, 232, 153)),
            (26, 62, 64, (246, 193, 119)),
            (26, 29, 30, (120, 143, 161)),
            (30, 23, 24, (103, 128, 148)),
        ),
    )


@contextmanager
def terminal_session(input_fd: int):
    settings = termios.tcgetattr(input_fd)
    try:
        tty.setcbreak(input_fd)
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[H\x1b[2J")
        sys.stdout.flush()
        yield
    finally:
        try:
            termios.tcsetattr(input_fd, termios.TCSANOW, settings)
        finally:
            sys.stdout.write(RESET + "\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()


def fit_frame(pixels: list[list[RGB]], columns: int, rows: int) -> list[list[RGB]]:
    height, width = len(pixels), len(pixels[0])
    scale = min(1, columns / width, 2 * rows / height)
    if scale == 1:
        return pixels
    fit_width, fit_height = max(1, round(width * scale)), max(1, round(height * scale))
    source_x = [int((x + 0.5) * width / fit_width) for x in range(fit_width)]
    return [
        [pixels[int((y + 0.5) * height / fit_height)][x] for x in source_x]
        for y in range(fit_height)
    ]


def draw(state: PlayState, size: os.terminal_size, phase: int, resized: bool) -> None:
    columns = max(0, size.columns - 1)
    controls = "   ".join(
        [f"{index} {target.name}" for index, target in enumerate(state.scene.targets, start=1)]
        + ["Q Quit"]
    )
    prefix = "\x1b[H" + ("\x1b[2J" if resized else "")
    message = "Resize terminal (Q quits)" if columns >= 25 else "Resize (Q quits)"
    lines = [message[:columns]]
    if columns >= 24:
        control_lines = textwrap.wrap(controls, width=columns)
        messages = [state.scene.intro]
        for target in state.scene.targets:
            messages.extend((target.text, target.blocked))
        needed_rows = max(len(textwrap.wrap(text, width=columns)) for text in messages)
        dialogue_rows = min(needed_rows, 3, max(1, size.lines - len(control_lines) - 4))
        art_rows = size.lines - len(control_lines) - dialogue_rows - 2
        if art_rows >= 2:
            title = textwrap.shorten(state.scene.title, width=columns, placeholder="...")
            art = encode_frame(fit_frame(state.pixels(phase), columns, art_rows))
            dialogue = textwrap.wrap(state.dialogue, width=columns, max_lines=dialogue_rows,
                                     placeholder="...")
            dialogue.extend([""] * (dialogue_rows - len(dialogue)))
            lines = [title, *art.split("\n"), "", *dialogue, *control_lines]
    sys.stdout.write(prefix + "\x1b[K\r\n".join(lines) + "\x1b[K\x1b[J")
    sys.stdout.flush()


def play(scene: Scene) -> None:
    input_fd, output_fd = sys.stdin.fileno(), sys.stdout.fileno()
    state = PlayState(scene)
    size = None
    phase = 0
    needs_draw = True
    with terminal_session(input_fd):
        next_frame = time.monotonic() + FRAME_INTERVAL
        while True:
            now = time.monotonic()
            current_size = os.get_terminal_size(output_fd)
            resized = current_size != size
            size = current_size
            if scene.flicker and now >= next_frame:
                phase ^= 1
                next_frame = now + FRAME_INTERVAL
                needs_draw = True
            if needs_draw or resized:
                draw(state, size, phase, resized)
                needs_draw = False
            timeout = SIZE_INTERVAL
            if scene.flicker:
                timeout = min(timeout, max(0, next_frame - time.monotonic()))
            ready, _, _ = select.select([input_fd], [], [], timeout)
            if ready:
                keys = os.read(input_fd, 64).lower()
                if not keys or b"q" in keys or b"\x04" in keys:
                    return
                for key in keys:
                    index = key - ord("1")
                    if 0 <= index < len(scene.targets):
                        state.interact(index)
                        needs_draw = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--prompt", help="ask a text model to make a new scene")
    source.add_argument("--scene", type=Path, help="play a saved scene JSON file")
    parser.add_argument("--model", help="override the scene generation model")
    parser.add_argument("--save-scene", type=Path, help="save generated scene JSON before play")
    args = parser.parse_args()
    if args.prompt is None and (args.model is not None or args.save_scene is not None):
        parser.error("--model and --save-scene require --prompt")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        parser.error("play requires a terminal on stdin and stdout")

    try:
        if args.prompt is not None:
            from generate_scene import generate_scene

            print("Generating scene...", file=sys.stderr, flush=True)
            scene, data = generate_scene(args.prompt, args.model)
            if args.save_scene is not None:
                args.save_scene.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        elif args.scene is not None:
            from scene import parse_scene

            scene = parse_scene(json.loads(args.scene.read_text(encoding="utf-8")))
        else:
            scene = tavern()
        play(scene)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
