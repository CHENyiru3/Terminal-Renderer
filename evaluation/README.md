# Evaluation

How reliably can GPT models turn a text prompt into a playable terminal scene? How much time and usage does each output take? The same renderer, scene format, and test prompts are used across models. The [five draft prompts](prompts.md) are divided into three interactive cases and two visual-fidelity cases.

| Case | What it tests | What to show in the blog |
| --- | --- | --- |
| White Bear Forest | Outdoor depth, readable wildlife silhouette, and a state change at a fixed anchor | Forest before and after opening the blind |
| At Home with a Cat and Dog | Two distinct animals in a furnished interior, each with its own interaction | Cat at the window and dog ready to play |
| Global World Map | Geographic recall and coastline accuracy at low resolution | Generated map beside a matching reference and a land-mask difference image |
| The Elf Gatekeeper | Recognizable character, conditional dialogue, and a visible transition | Locked arch, lit brazier, and open passage |
| The Starry Night | Recognition, composition, palette, and brushstroke-like structure in pixel art | Generated study beside the MoMA reference |

## Comparison protocol

1. Query `model/list` through the signed-in Codex App Server and record the date, CLI version, and catalog response. Use every picker-visible GPT model listed for the account that advertises `medium` reasoning. Record visible GPT models that lack `medium` and models that fail to start as coverage exceptions. Use a successful scene run to verify access and record any model substitution exposed in the logs. [Codex model discovery](https://developers.openai.com/codex/app-server#list-models-modellist)
2. Set Codex reasoning explicitly with `-c 'model_reasoning_effort="medium"'`. Use standard speed, fresh sessions, the same renderer revision and shared format instructions, and the same local machine. Keep the tasks text-only and use the map data and painting image during scoring. Run one request at a time. Record the selected model, requested effort, CLI version, renderer revision, speed setting, and prompt version with each result. [Codex config reference](https://developers.openai.com/codex/config-reference)
3. Run all five cases on one eligible model as a pilot to check the format and scoring. If the prompts or harness change, keep those pilot outputs separate. Freeze both for the scored run and collect three trials per model per case, with a fixed-seed shuffled order for each repeat. Record that seed. Three trials provide a descriptive view of variability.
4. Preserve and score the first attempt. If JSON parsing or scene validation fails, allow one repair using the same model and effort with the exact validator error. Keep both attempts and report first-pass and post-repair validity. Attempts that produce valid but weak art or fail a gameplay check remain in the results as produced.
5. Interpret the results as performance through the Codex CLI and this renderer. The current scene generator requires at least one object and supports rectangles and polygons of up to 12 vertices. For the two static cases, the benchmark harness will need to accept `objects: []` and pass the same RGB framebuffer to the renderer. Keep the same 144 × 80 canvas and 64-background-shape cap across the suite. A fixed geometry budget makes the comparisons reproducible and constrains the maximum fidelity of the map and painting.

## Checks and quality scoring

- **Interactive cases.** Verify the interaction sequence specified in [the prompts](prompts.md). Check that each number key retains its target, objects fit within distinct bounds, blocked actions preserve the scene, and successful actions persist when switching targets or resizing. On a repeat press, compare the framebuffer without selection markers to confirm no extra state change. Score visual composition, subject readability, and interaction feedback independently.
- **World map.** Rasterize Natural Earth's 1:110m land polygons using the same projection, viewport, orientation, and resolution. Extract the generated land mask from the rendered land color. Report land intersection over union (IoU) and visually check the placement of the Americas, Africa, Eurasia, Australia, Greenland, and Antarctica. Evaluate only the 144 × 72 map viewport. [Natural Earth land data](https://www.naturalearthdata.com/downloads/110m-physical-vectors/)
- **The Starry Night.** Score composition and palette separately. Inspect the shapes and relative positions of the left cypress, central sky swirl, upper-right moon, hills, and village with its steeple. Compare only the 100 × 80 painting viewport and present the reference alongside the generated output. [MoMA reference](https://www.moma.org/collection/works/79802)

For subjective criteria, use a 0–4 scale with model IDs hidden during review. **0** means absent or unrecognizable, **1** means a major miss, **2** means partly successful, **3** means clear with minor flaws, and **4** means clear and closely matches the case. Save the per-criterion scores and one sentence explaining each rating. Report playable-scene check results and visual fidelity separately.

## Tokens, cost, and time

| Measure | What to record |
| --- | --- |
| Tokens | Input, cached input, output, and reasoning output from each reported Codex `turn.completed` usage event. Use blank values when telemetry is missing. [Codex JSONL output](https://developers.openai.com/codex/noninteractive) |
| Time | Wall-clock seconds from launching generation to the first validation result. If a repair is attempted, also record total time through the final validation result. Time rendering separately. Report the median and range per model and case, with the valid sample count. |
| Subscription usage | Per-run credits when exposed by Codex. An accountwide allowance change can be recorded at batch level when no other workload shares the allowance during the batch. Use unavailable for individual runs when there is no per-run readout. [Codex subscription usage](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan) |
| API-equivalent cost | Optional USD estimate using the dated standard API rates for the precise model and rate tier. Apply cached rates only to reported cache hits. Keep the estimate blank when the model's matching rates or necessary token categories are unavailable. [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) |

Calculate the optional API estimate as ((input − cached input) × input rate + cached input × cached-input rate + output × output rate) / 1,000,000. Use total billable output, including reasoning. Check whether the reported output total already includes reasoning before adding a separately reported reasoning count. Report actual subscription credits or spend only when the subscription exposes them. [Reasoning token accounting](https://developers.openai.com/api/docs/guides/reasoning)

## Output archive

Keep one directory per model, case, and trial. Save the exact request, raw responses, JSONL events, validation outcomes, timing and token records, and each successful scene JSON. Save a native 144 × 80 PNG and a consistently enlarged nearest-neighbor copy for the gallery. For interactive scenes, save the initial frame and the frame after each scripted key press. Include scores, notes, and failure reasons. The blog can show representative frames and link to the full gallery, including failed attempts and retry outcomes.

This section defines the prompts and protocol. The account catalog and model results will be populated during the benchmark run.
