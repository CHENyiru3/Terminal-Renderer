"""Generate editable scene data from a text prompt."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scene import Scene, parse_scene

INSTRUCTIONS = """Create one fixed-camera pixel-art game scene from the user's prompt.
Return a JSON object with these fields:
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
rectangle sizes and 3-12 polygon vertices. Shapes must fit entirely inside
the canvas. Object art uses absolute coordinates and must fit inside its bounds.
Objects render in array order over the background. Use distinct, legible silhouettes,
layered backgrounds, shadows, highlights and small details. Fill the canvas.
Give objects specific actions the player can take and a visible place in the scene.

An object may include "after" with 1-24 additional shapes inside its own bounds,
drawn permanently after successful interaction. Use it to show a clear change.
An object may require another object's successful interaction, with "requires"
set to that object's exact name and "blocked" giving a clue (up to 240 characters).
Avoid cycles. Include a simple cause-and-effect interaction when it fits the prompt.
"""


def generate_scene(prompt: str, model: str | None = None) -> tuple[Scene, dict]:
    """Request scene JSON and retry once with feedback if validation fails."""
    if not prompt.strip():
        raise ValueError("the scene prompt is empty")
    base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and base_url.rstrip("/") == "https://api.openai.com/v1":
        raise ValueError("set OPENAI_API_KEY to generate a scene")
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        content = _complete(base_url, api_key, model, messages)
        try:
            data = json.loads(content)
            return parse_scene(data), data
        except ValueError as error:
            if attempt == 1:
                raise ValueError(f"the model returned invalid scene JSON: {error}") from error
            messages.extend([
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Fix this validation error and return all scene JSON: {error}"},
            ])


def _complete(base_url: str, api_key: str | None, model: str, messages: list[dict]) -> str:
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
