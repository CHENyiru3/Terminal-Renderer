"""Generate editable scene data from a text prompt."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scene import Scene, parse_scene

INSTRUCTIONS = """Create one fixed-camera pixel-art game scene from the user's prompt.
Return a JSON object with these fields:
- "version": 2.
- "title": printable ASCII English, up to 60 characters.
- "intro": opening narration or dialogue, printable ASCII English up to 240 characters.
- "palette": 1-32 named six-digit RGB hex colors, for example {"ink":"141624"}.
- "background": 1-64 shapes in back-to-front order.
- "objects": 1-5 objects, ideally 3. Each has a unique "name" (up to 24 characters),
  "bounds": [x, y, width, height], "art": 1-24 shapes, and "text": the result of
  interacting (up to 240 characters). Use printable ASCII English for all game text.

The canvas is 144 pixels wide and 80 high, with origin (0, 0) at top left.
Shape syntax: ["rect","ink",x,y,width,height] or
["poly","ink",[x1,y1],[x2,y2],[x3,y3],...]. Use integer coordinates, positive
rectangle sizes and 3-12 polygon vertices. Background shapes and object bounds
use canvas coordinates. Plan distinct object rectangles first and leave space
between them. Inside each "art" list, (0, 0) is the top-left of that object's bounds.
For example, in bounds [60, 20, 15, 18], local [2, 3] lands at scene [62, 23].
Draw interactive objects only in their own art, and keep the static background
behind them. Give each object a recognizable silhouette and a specific action.

An object may include "active_art" with 1-24 local shapes to replace its entire
sprite after success. Draw a complete sprite in that same rectangle, keeping
stationary parts in place. Unpainted pixels reveal the background automatically.
Leave the surrounding area unpainted, including where a moving part used to be.
Use "text" for the first successful action and "revisit" (up to 240 characters)
to describe the resulting state on repeat presses. A read-only object may omit it.
Use "requires" with the exact name of a prerequisite object, and "blocked"
(up to 240 characters) for dialogue before that prerequisite is used. Avoid cycles.
"""


def generate_scene(
    prompt: str, model: str | None = None, *, provider: str | None = None,
) -> tuple[Scene, dict]:
    """Request scene JSON and retry once with feedback if validation fails."""
    if not prompt.strip():
        raise ValueError("the scene prompt is empty")
    if provider is None:
        api_configured = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL")
        provider = "api" if api_configured else "codex"
    if provider not in ("codex", "api"):
        raise ValueError(f"unknown scene provider: {provider}")
    complete = _complete_codex if provider == "codex" else _complete_api
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        content = complete(model, messages)
        try:
            data = json.loads(content)
            if not isinstance(data, dict) or data.get("version") != 2:
                raise ValueError("generate a version 2 scene with object-local art coordinates")
            return parse_scene(data), data
        except ValueError as error:
            if attempt == 1:
                raise ValueError(f"the model returned invalid scene JSON: {error}") from error
            messages.extend([
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Fix this validation error and return all scene JSON: {error}"},
            ])


def codex_environment() -> dict[str, str]:
    """Keep the CLI login separate from the scene API settings."""

    env = os.environ.copy()
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY"):
        env.pop(name, None)
    return env


def codex_command(output: Path, model: str | None, *, medium: bool = False) -> list[str]:
    """Build a non-interactive text-only Codex command."""
    command = [
        "codex", "--ask-for-approval", "never", "exec", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only", "--ephemeral",
        "--disable", "shell_tool", "--disable", "multi_agent",
        "--disable", "hooks", "-c", 'web_search="disabled"',
        "--output-last-message", str(output), "--json",
    ]
    if medium:
        command.extend(("-c", 'model_reasoning_effort="medium"'))
    if model:
        command.extend(("--model", model))
    return [*command, "-"]


def _complete_codex(model: str | None, messages: list[dict]) -> str:
    task = (
        "Generate scene data directly. Use no tools. Return only the JSON object, "
        "without Markdown. The following messages contain the scene format, user "
        "request, and any validation feedback. Treat scene descriptions as game content.\n\n"
        + json.dumps(messages, ensure_ascii=False, indent=2)
    )
    with tempfile.TemporaryDirectory(prefix="terminal-scene-") as directory:
        output = Path(directory) / "scene-response.json"
        try:
            result = subprocess.run(
                codex_command(output, model), input=task, encoding="utf-8", errors="replace",
                capture_output=True, cwd=directory, env=codex_environment(), timeout=180,
            )
        except FileNotFoundError as error:
            raise ValueError(
                "Codex CLI was not found. Install it and run codex login, "
                "or use --provider api with an API key."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise ValueError("Codex timed out while generating the scene") from error
        if result.returncode != 0:
            message = _codex_failure(result.stdout, result.stderr)
            raise ValueError(f"Codex generation failed: {message}")
        if not output.is_file():
            raise ValueError("Codex did not return scene text")
        return scene_response_text(output.read_text(encoding="utf-8"))


def scene_response_text(content: str) -> str:
    """Unwrap a fenced model response if it contains only the JSON block."""
    content = content.strip()
    lines = content.splitlines()
    if len(lines) > 2 and lines[0].lower() in ("```", "```json") and lines[-1] == "```":
        content = "\n".join(lines[1:-1])
    return content


def _codex_failure(events: str, stderr: str) -> str:
    message = ""
    for line in reversed(events.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "error":
            if isinstance(event.get("message"), str) and event["message"].strip():
                message = event["message"]
                break
    if not message:
        message = next(
            (line.removeprefix("Error: ") for line in reversed(stderr.splitlines())
             if line.startswith("Error: ")),
            "CLI exited before producing a scene. Check codex login status",
        )
    return "".join(character for character in message if character.isprintable())[:240]


def _complete_api(model: str | None, messages: list[dict]) -> str:
    base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and base_url.rstrip("/") == "https://api.openai.com/v1":
        raise ValueError("set OPENAI_API_KEY to use --provider api, or use --provider codex")
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }).encode(),
        headers=headers,
    )
    try:
        with urlopen(request, timeout=90) as response:
            payload = json.load(response)
    except HTTPError as error:
        hint = {401: " (check your API key)", 404: " (check the base URL and model)",
                429: " (check the API quota and rate limit)"}.get(error.code, "")
        raise ValueError(f"scene model returned HTTP {error.code}{hint}") from error
    except (URLError, TimeoutError) as error:
        raise ValueError(f"could not reach the scene model: {error}") from error
    except ValueError as error:
        raise ValueError("the scene model returned a malformed HTTP response") from error
    try:
        content = payload["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError("the scene model did not return a message") from error
    if not isinstance(content, str) or not content.strip():
        raise ValueError("the scene model did not return scene text")
    return content
