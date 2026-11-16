# Terminal Renderer

Describe a place and what the player can do there. A text model builds a fixed-camera pixel scene with one to five interactive objects. Each object gets a numbered key, a selection outline, and an interaction response. Interacting with an object can change its appearance or unlock an action on another object.

## Play

Use Python 3.11 or newer on macOS or Linux, in a UTF-8 terminal that supports ANSI truecolor, the alternate screen, and the `▀` glyph. The standard library is sufficient.

```sh
python3 demo.py
```

In the included Lighthouse Tavern, press **1** to read the wet letter, **2** to speak to the innkeeper, or **3** to inspect the back door. Press **Q** or **Ctrl-C** to return to the shell. The lantern flickers between key presses. The scene scales down as the terminal shrinks. The tavern displays at its native size in a terminal of at least 145 columns and 44 rows.

## Generate a scene

Use a recent [Codex CLI](https://developers.openai.com/codex/cli) signed in with ChatGPT. Run `codex login status` to check your session, or `codex login` to sign in.

```sh
python3 demo.py --provider codex --prompt "A moonlit greenhouse. Light a brass lantern to find a key, inspect a seed tray, and use the key to unlock the iron gate." --save-scene greenhouse.json
```

Generation runs before play. Codex CLI uses its own signed-in session. Choose a different Codex model with `--model`.

Without `--provider`, the app uses Codex CLI when neither `OPENAI_API_KEY` nor `OPENAI_BASE_URL` is set. Use `--provider api` for an OpenAI-compatible endpoint that supports Chat Completions JSON mode. The API mode defaults to `gpt-4.1-mini` and also accepts `--model` or `OPENAI_MODEL`.

Replay your saved scene or try the bundled greenhouse with no API key:

```sh
python3 demo.py --scene greenhouse.json
python3 demo.py --scene examples/greenhouse.json
```

In the bundled greenhouse, try **3 → 1 → 3** to check the locked gate, light the lantern and find the key, then open the gate. The model supplies the scene and dialogue up front. Object state lasts for the current play session.

### Scene JSON

The [greenhouse example](examples/greenhouse.json) shows the full format. A scene has a title, opening dialogue, named RGB hex colors, a list of background shapes, and a list of objects. Shapes are painted in order on a 144 × 80 pixel canvas:

- `["rect", "color", x, y, width, height]` draws a filled rectangle.
- `["poly", "color", [x1,y1], [x2,y2], [x3,y3], ...]` draws a filled polygon.

Each object has a unique name, a bounding rectangle `[x, y, width, height]`, an `art` list within that rectangle, and `text` for a successful interaction. Optional `after` shapes appear on success. Optional `requires` names another object that must have been used first, and `blocked` provides the clue shown when that requirement is unmet. Coordinates are absolute, with the origin at the top left. Use printable ASCII for in-game text.

## Renderer API

```python
from terminal_renderer import encode_frame

frame = [[(220, 140, 70)], [(32, 48, 80)]]
encoded = encode_frame(frame)  # One colored half-block cell.
```

`encode_frame(rows, *, pad=(0, 0, 0)) -> str` takes a nonempty rectangular sequence of 8-bit RGB triples. It puts the upper pixel in the foreground and the lower pixel in the background. The optional RGB pad supplies the lower pixel for odd-height frames. It returns newline-separated rows with a color reset at each row end and no trailing newline. The caller handles sizing, compositing, and terminal writes.

```sh
python3 -m unittest -v
```
