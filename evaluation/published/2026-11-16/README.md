# Terminal scene benchmark · 16 November 2026

**17 of 40 scenes passed format validation on the first response.** This run used eight GPT models, five prompts, medium reasoning, a 144 × 80 canvas, and 40 workers. Batch elapsed time was 146.499 seconds.

Download [gallery.html](gallery.html) from its GitHub file page and open it in a browser to compare the 17 passing scenes and their 87 captured frames. The gallery includes time, tokens, an API-equivalent cost estimate, and downloadable scene JSON for each passing output.

## Results by model and case

Linked cells show a valid result and its wall-clock time through validation. Each opens its replayable scene JSON. Invalid responses retain their times and error messages in the [40-attempt CSV](summary.csv).

| Model | Forest | House | World map | Elf gatekeeper | The Starry Night | Valid |
| --- | --- | --- | --- | --- | --- | ---: |
| GPT-6.1 Sol | Invalid · 105.0 s | [88.0 s](scenes/house/gpt-6.1-sol.json) | [73.3 s](scenes/map/gpt-6.1-sol.json) | [115.6 s](scenes/elf/gpt-6.1-sol.json) | [86.1 s](scenes/starry-night/gpt-6.1-sol.json) | **4/5** |
| GPT-6 Astra | [118.2 s](scenes/forest/gpt-6-astra.json) | [105.8 s](scenes/house/gpt-6-astra.json) | [100.3 s](scenes/map/gpt-6-astra.json) | [129.0 s](scenes/elf/gpt-6-astra.json) | Invalid · 110.0 s | **4/5** |
| GPT-6.1 Terra | Invalid · 82.1 s | [61.8 s](scenes/house/gpt-6.1-terra.json) | Invalid · 61.7 s | [63.9 s](scenes/elf/gpt-6.1-terra.json) | Invalid · 67.9 s | **2/5** |
| GPT-6 Sol | [113.3 s](scenes/forest/gpt-6-sol.json) | [67.1 s](scenes/house/gpt-6-sol.json) | [87.3 s](scenes/map/gpt-6-sol.json) | [114.4 s](scenes/elf/gpt-6-sol.json) | Invalid · 70.8 s | **4/5** |
| GPT-6 Luna | Invalid · 79.9 s | [61.2 s](scenes/house/gpt-6-luna.json) | Invalid · 40.1 s | Invalid · 47.2 s | Invalid · 53.2 s | **1/5** |
| GPT-5.6 Sol | Invalid · 145.1 s | Invalid · 133.1 s | [113.9 s](scenes/map/gpt-5.6-sol.json) | [146.4 s](scenes/elf/gpt-5.6-sol.json) | Invalid · 113.1 s | **2/5** |
| GPT-5.6 Terra | Invalid · 81.8 s | Invalid · 58.4 s | Invalid · 43.7 s | Invalid · 70.8 s | Invalid · 55.8 s | **0/5** |
| GPT-5.6 Luna | Invalid · 56.9 s | Invalid · 47.6 s | Invalid · 47.3 s | Invalid · 64.7 s | Invalid · 46.3 s | **0/5** |
| **Valid** | **2/8** | **5/8** | **4/8** | **5/8** | **1/8** | **17/40** |

## Replay and evidence

From the repository root:

```sh
python3.11 demo.py --scene evaluation/published/2026-11-16/scenes/forest/gpt-6-sol.json
```

- [Scene JSON and initial artwork](scenes) contains one replayable scene and one PNG for each passing output, organized by case.
- [Automated scene checks](checks.json) contains gameplay and layout checks. The map reference comparison and subjective visual scores were unmeasured in this run.
- [Run settings and source hashes](run.json), [batch timing](batch.json), and [exact prompts](../../prompts.md) document the run. The [evaluation protocol](../../README.md) explains the measurements.

The measurements are single observations for each model and case under concurrent load. Estimated USD uses the dated rate snapshot in the run settings. Subscription-credit measurements were unavailable.
