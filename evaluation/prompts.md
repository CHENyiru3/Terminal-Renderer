# Terminal scene benchmark prompts

Use the shared instructions once, followed by one case prompt verbatim. References named in the evaluation guide are for scoring. Case titles and scripted checks outside the code blocks are evaluator notes.

## Shared instructions

```text
Return one version-2 scene JSON object. Use a fixed 144 by 80 pixel canvas with origin at the top left, a palette of at most 32 named six-digit RGB colors, and up to 64 background shapes drawn in back-to-front order. Draw using ["rect","color",x,y,width,height] and ["poly","color",[x1,y1],[x2,y2],[x3,y3],...] with integer coordinates. Polygons have 3 to 12 vertices. Include "version", "title", "intro", "palette", "background", and "objects". Use printable ASCII English for the title (up to 60 characters), intro and interaction text (up to 240 characters), and object names (up to 24 characters).

For an interactive scene, put the three objects in the exact order requested. Give each one a distinct, non-overlapping bounds rectangle [x,y,width,height] in canvas coordinates and 1 to 24 local art shapes. Draw the sprite relative to its own rectangle in both "art" and optional "active_art". The active art fully replaces the initial art at the same anchor. Keep stationary parts in place and leave unused pixels unpainted. Use "text" for first success, "revisit" for the current state on repeat presses, and "requires" with the exact prerequisite name plus "blocked" for a precondition. Keep interactive sprites out of the static background.

For a visual study, use "objects": [] and place all art in the background. Return the JSON only. Use text-to-scene reasoning without tools, online references, images, or external data.
```

## 1. White Bear Forest

```text
At dawn in a beautiful boreal forest, you discover a white bear across a stream. Build a single wide view with layered pine trees, mist behind them, a winding reflective stream, and warm light reaching the forest floor. Draw the white bear large enough to recognize against the darker far bank. Place a wooden lookout blind and a weathered trail sign on the near bank.

Use these objects in order: 1 Trail sign, 2 Lookout blind, 3 White bear. Reading the sign explains that opening the lookout's viewing slit gives a clear view of the bear. Opening the blind visibly exposes the slit, and it stays open. Viewing the bear before opening the blind gives an obscured-view message. After opening the blind, viewing the bear reveals that it lifts its head. Change the bear's head pose within the same bounds and describe that pose on repeat visits.
```

Check **3 → 1 → 2 → 3 → 3**. The blind opens once and the bear keeps its new pose.

## 2. At Home with a Cat and Dog

```text
Build a modern living room in late-afternoon light. Show a wide window, a low sofa, warm wood flooring, and clear floor space. A cat sits on a window perch and a dog rests near the sofa. Use distinct silhouettes and readable poses for both animals.

Use these objects in order: 1 Cat, 2 Toy basket, 3 Dog. Interacting with the cat makes it sit upright and purr. Opening the toy basket reveals a ball and leaves the lid visibly open. Before the basket is opened, the dog watches you from its resting spot. After the basket is opened, interacting with the dog makes it stand in an eager play pose within the same bounds. The cat, basket, and dog retain their new appearances. Repeat visits describe their current states.
```

Check **3 → 1 → 2 → 3 → 1 → 3**. Revisit the cat and dog after the dog changes pose.

## 3. Global World Map

```text
Draw a geographically recognizable physical world map in a north-up equirectangular projection. Put the entire map inside the 144 by 72 pixel viewport at x=0 through 143 and y=4 through 75. Use longitude -180 to +180 left to right and latitude +90 to -90 top to bottom. Center longitude 0 at the middle column boundary and put the Pacific split at the left and right edges.

Use exactly two colors inside the viewport: land #D6D3A5 and ocean #294B65. Use a dark matte outside it. Show the major continental shapes, Greenland, Australia, and Antarctica. Preserve recognizable features such as Central America, the Arabian Peninsula, India, and the separation between Australia and Southeast Asia at this resolution. Draw no labels, graticule, borders, or markers. Set objects to an empty array.
```

Score land-mask IoU and geographic landmarks against Natural Earth. Small islands may be simplified at 144 × 72.

## 4. The Elf Gatekeeper

```text
At twilight in a magical woodland, a woman elf guards an ancient stone arch. Frame the arch among luminous mushrooms and ferns, with a small brazier nearby and a dark path leading to the foreground. Make the elf recognizable by her pointed ears, profile, and silhouette, using a teal cloak against the violet setting.

Use these objects in order: 1 Elf gatekeeper, 2 Moonfire brazier, 3 Rune arch. Speaking to the elf gives the clue that the arch responds to moonfire. Lighting the brazier changes it from a dark bowl to a blue flame and leaves it lit. Inspecting the arch before the brazier is lit reveals dormant runes. After the brazier is lit, interacting with the arch makes its runes glow and reveals an open passage. Keep the standing stones in the same positions. Repeat visits describe the lit brazier and open arch.
```

Check **3 → 1 → 2 → 3 → 2 → 3**. The final two presses should describe and preserve their active states.

## 5. The Starry Night

```text
Reproduce the composition of Vincent van Gogh's 1889 painting The Starry Night as a terminal pixel-art study. Use the centered 100 by 80 pixel viewport at x=22 through 121 and y=0 through 79. Fill the side margins with a uniform dark matte. Preserve the dark, flame-shaped cypress on the left, the broad curling blue sky in the center, the yellow moon toward the upper right, the glowing stars, and the low village and church steeple below the rolling hills.

Layer curved-looking runs of color to suggest the sky's brushstrokes and use deep blues, yellow highlights, and dark blue-green land. Spend detail first on the placement and silhouettes of the major motifs. Set objects to an empty array.
```

Score layout, recognizable motifs, and palette against the MoMA painting.
