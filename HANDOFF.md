# Terminal Renderer handoff

## Implementation prompt

Build and test the first version of a reusable terminal pixel renderer in [CHENyiru3/Terminal-Renderer](https://github.com/CHENyiru3/Terminal-Renderer). The demo is a fixed-camera tavern with a selectable letter, innkeeper, and back door. It should remain on screen, respond to keys, and redraw in place until the player exits. Use English for source comments, documentation, and demo dialogue. Keep the demo code direct enough to read alongside the renderer in one sitting.

### Scope and file layout

Use Python 3.11+ and its standard library for a first pass targeting macOS and Linux. Run the demo with `python3 demo.py`. Keep the renderer and demo independent of model APIs, image codecs, and graphical terminal protocols.

| File | Responsibility |
| --- | --- |
| `terminal_renderer.py` | Encode a rectangular RGB framebuffer as truecolor terminal half-block rows. |
| `demo.py` | Load the fixture, run the terminal session and input loop, render overlays, and show dialogue. |
| `examples/tavern.txt` | Copy the exact text fixture from the appendix. |
| `test_terminal_renderer.py` | Exercise the encoder without a real terminal. |
| `README.md` | Document the public API, run and test commands, controls, and terminal requirements. |

### Renderer contract

Expose `encode_frame(rows, *, pad=(0, 0, 0)) -> str`. Input is a nonempty rectangle of RGB triples in row-major order, with the origin at the top left. Reject empty, ragged, or invalid RGB input with `ValueError`. Keep the function pure so the same frame always produces the same output.

- Encode each vertical pair as `▀`. Use ANSI truecolor foreground `38;2;r;g;b` for the upper pixel and background `48;2;r;g;b` for the lower pixel. Use `pad` for the missing lower pixel of an odd-height frame. An RGB frame of `W × H` pixels occupies `W × ceil(H/2)` terminal cells.
- Reset color at the end of each encoded row. Return newline-separated rows without a trailing newline. Reuse the active color pair for consecutive cells within a row. Leave cursor movement, terminal sizing, compositing, and writes to the caller.

### Demo behavior

1. Load the indexed-color text fixture into an immutable RGB background. For a redraw, copy the background and apply the current selection highlight and a subtle two-frame rain or lantern effect. Paint changes in source-pixel coordinates before scaling. Keep the art and scripted dialogue out of the renderer module.
2. Start an interactive terminal session with an alternate screen and hidden cursor. On macOS and Linux, use `termios` and `tty.setcbreak` for key input, `select` with a timeout to wait for input or the next frame, and `time.monotonic` to schedule frames. Use `try/finally` to restore the original input settings, visible cursor, screen, and default color on quit, Ctrl-C, and exceptions. Check that stdin and stdout are terminals before changing either.
3. Reserve room for a title, dialogue, and controls. Display the native 144 × 80 artwork as 144 columns × 40 graphic rows when space permits. Reserve one spare terminal column to avoid a right-margin wrap. For smaller views, use a nearest-neighbor fit that preserves the pixel aspect ratio. On resize, clear the stale frame and redraw. When space is insufficient for the title, scene, and controls, write a short resize message and keep Quit responsive.
4. `1` examines the wet letter, `2` speaks to the innkeeper, `3` examines the back door, and `q` exits. On selection, update both the dialogue and the small corner markers around the target. Start with the innkeeper’s greeting. Keep the ongoing animation subtle and keep input responsive while it runs. Home the cursor before each redraw and flush the frame and dialogue together.

| Key | Target rectangle `(x, y, width, height)` | Suggested dialogue |
| --- | --- | --- |
| `1` | `(55, 61, 14, 9)` | The ink has run, but the wax is intact. The seal shows an upside-down lighthouse. |
| `2` | `(77, 30, 19, 22)` | Keep your voice down. Someone has been waiting beyond the back door. |
| `3` | `(108, 24, 27, 33)` | A cold draft slips through the gap. You hear two short knocks. |

Suggested greeting from the innkeeper: `You came from the lighthouse? Sit down. Someone has been waiting for you to open that letter.`

The future game can supply the same framebuffer from an LLM-authored scene definition or a pixel grid. For this milestone, treat scene generation, NPC agents, and save files as future callers of the renderer.

### Verification and delivery

- Run `python3 -m unittest -v`. Cover RGB ordering and half-block orientation, odd-height padding, row shape and invalid-input handling, expected visible dimensions after stripping ANSI, color reset, and color-pair reuse. Include a test that loads the fixture or checks the decoded dimensions if it can use the same straightforward loader as the demo.
- Run `python3 demo.py` in a truecolor terminal. Check the native-size frame when space permits and a smaller terminal size. Exercise all three keys, watch the animation continue between key presses, shrink and re-expand the window, and verify that both `q` and Ctrl-C restore the shell. If a physical terminal is unavailable, use a pseudo-terminal for input, resize, and cleanup, and record which visual checks still require a human terminal.
- Report the exact commands and outcomes, with any remaining manual checks. The first milestone is complete when both a reusable encoder and the interactive demonstration have been exercised.

## Confirmed starting point

- The GitHub repository was empty before this handoff. The renderer and native TUI are pending.
- The in-chat preview was an HTML canvas drawn by explicit pixel fill operations. Its three target interactions were exercised with a mocked canvas and event handler. The preview used scripted dialogue.
- A separate 8 × 8 experiment verified the RGB half-block ordering and emitted dimensions. The appendix captures the preview’s initial 144 × 80 framebuffer, including all 77 colors, before any target is selected.
- The Python baseline, renderer interface, and controls above are implementation choices for the first pass. The text fixture and renderer deliberately share only an RGB framebuffer.

## Exact preview fixture

<details>
<summary>Expand the 144 × 80 tavern fixture</summary>

The first three lines contain dimensions, palette symbols, and six-digit RGB colors in matching order. Each remaining line is one top-to-bottom pixel row. Copy the block contents directly to `examples/tavern.txt`.

```text
144 80
0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+,-./:;
1a1721 6f4940 30212a 3b2931 805647 47323b 573b3c 755049 563a3d 67443e 75715e 6e7a70 985c49 4b6682 533e42 718da2 9b6c4f 7d7759 283446 56738c 926044 61768c 91a6b1 b27e52 344052 edb569 395570 fff0b4 8a5e49 536275 28252e 3a262c 52373a 405670 503039 9d6a4d 765044 d29a69 ad7655 2a465f 27364a 7790a0 a66c55 766753 b18e63 a7a18b 697770 9d6d53 9f7654 a77350 32232b 68443e 2f262f 4e3538 352931 45363a f8ebaf 5b4240 576375 eaab5a 2a222c f3d48b ac7750 404f62 c28a59 e6cf9c e0b267 745147 ca6950 9b433c 805144 775746 e0a771 221c26 65423b 59383a 392831
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111
111112222211111111111111111111111111111111111111111111111111111111111111111111111111111111111111111112222111111111111111111111111111111111111111
333332222433333333333333333333333333333333333333333333333333333333333333333333333333333333333333333334222333333333333333333333333333333333333333
555552222456666666666666666666666666666666666666677777777777777777777777777777777777777777777777666664222555555555555555555555555555555555555555
555552222458600000000000000000000000000000000000000000666666686666666666666666666666668666666666666664222655555855555555555555555555555585555555
555552222458600000000000000000000000000000000000000000999999989999999999999999999999998999999966666664222655555855555555555555555555555585555555
555552222458600444444444444444444444444444444444444400999999989999999999999999999999998999999996666664222665555855555555555555555555555585555555
5555522224686004444444444444444444444444444444444444009999999899999999999999999A9999998999999996666664222665555855555555555555555555555585555555
3333322224333004444444444444444444444444444444444444003333333333333333B3333333AA3333333C33333333333334222333333333333333333333333333333333333333
555552222466600444DDDDDDDDDDDDDDDDEDDDFDDDDDDDDDD44400777777777777777BB777G777AA777777CC7777H777666664222666555555555555555555555555555555555555
555582222466600444DDDDDDDDDDDDDDDDEDDDFDDDDDDDDDD44400899999999999999BB99GG999AA999999CC999HH999666664222666555555555555555555555855555555555555
555582222466600444DDFDDDDDDDDDDDDDEDDDFDDDDDDDDDD44400899999999999999BB99GG999AA999999CC999HH999666664222666555555555555555555555855555555555555
555582222466600444DDFDDDDDDDDDDIIDEDDJDDDDDDDDDDD44400899999999999999BB99GG999AA999999CC999HH999966664222666655555555555555555555855555555555555
555582222466600444DDFDDDDDDDDDIIIIEDDJDDDDDDDFDDD4440089999999KK99444444444444444444444444444444966664222666655555555555555555555855555555555555
333332222433300444LJLDDDDDDDDIIIIIEIDDDDDDDDDFDDD4440033333KKKKKK32222222222222A2222222222222222333334222333333333333333333333333333333333333333
555552222466600444LJLLLLLLDDDDMMMMEDDDDDDDDDDFDDD444007777KKKKKNKK2222B2222222AA2222222C22222222996664222666665555555555555555555555555555555555
555552222486600444LLLLLLLLLLLDMMMMEDDDDDDDDDJDDDD44400999KKKNNNNNKK99BB999G999AA999998CC9999H999996664222666668500000000000000000055555855555555
555552222486600444LLLLLLDDDDDDOOOOEDDDDDDDDDJDDDD4440099KKNNNPPNNKKK9BB99GG999AA999998CC999HH999999664222666668000000000000000000005555855555555
555552222486600444QQQQQQQQQQQQOOOOEQQQQQQQQQQQQQQ444009KKNNN2PR2NKKK9BB99GG999AA999998CC999HH999999664222666660000SSSSSSSSSSSSSSS000555855555555
555552222486600444QQQQQQQQQQQQOTTOEQQQQQQQQQQQQQQ44400KKKNNN2PR2NNK99BB99GG999AA999998CC999HH99999966422266666000SSSSSSSSSSSSSSSSS00555855555555
333332222433300444QQQQQQFQQQQOOTTOEOQQQQQQQQQQQQQ44400KKKNNN2PP2NNK444444444444444444444444444443333342223333000SSSUUUUUUUUUUUUUSSS0033333333333
555552222466600444QQQQQQFQQQQOOTTOEOQQQQQQQQQQQQQ444007KNNNN2222NKK22222222222222222222222222222999964222666000SSSUUUUUUUUUUUUUUUSS0005555555555
555852222466600444EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE444009KKKVVVVVVVVK2222222222222222222222222222299999422266600SSSUUUUUUUUWWUUUUUUSSS005555555555
555852222466600444QFQQQJQQQQQOOTTOEOQQQQQQQQQQQQQ444009KKKVVVVVVVV99999999999989999900000999999999999422266600SSUUUUUUWWWWWUUUUXXXSS005555555555
555852222466600444QFQQQJQQQQQOOTTOEOQQQFQQQQQQQQQ4440099KKKKKKKKKK99999999999989999000000099999999999422266600SSUUWWWWWWWWWUUUUXXXSS005555555555
555852222466600444QFQQQQQQQQQOOTTOEOQQQFQQQQQQQQQ4440099999999999999999999999989990YZZZZYY09999999999422266600SSWWWWWWaWWWWUUUUXXXSS005555555555
333332222433300444JQQQQQQQQQQOOTTOEOQQQFQQQQQQQQQ4440033333333333333333333333333330YYYYYYY00333333333422233300SSWWWWWWaWWWWUUUUXXXSS003333333333
555552222466600444JQQQQQQFQQOOOTTOEOOQJQQQQQQQQQQ44400777777777777777777777777777700bbbbcYY0777799999422266600SSWWaWWWaWWWWUUUUXXXSS005555555555
555552222466600444dddddddFddOOOOOOEOOdJddddFddddd44400999998999999999999999999999900bbbbcYY0999999999422266600SSWWaWWWaWWWWUUUUXXXSS008555555555
555552222466600444dddddddFddOOOOOOEOOddddddFddddd44400999998999999999999999999999000b0bb0YY0999999999422266600SSWWaWWWaWWWWUUUUXXXSS008555555555
555552222466600444ddddddJeeeeeeeeeEedddddddFddddd44400999998999999999999999999999000bbbbcYY0999999999422266600SSWWaWWWaWWWWUUUUXXXSS008555555555
555552222466600444dddeeeJeeeeeeeeeEeedddddJdddddd44400999998999999999999999999999000bbbbcYY0999999999422266600SSWWaWWWaWWWWUUUUXfXSS008555555555
333332222433300444ddeeeeeeeeeeeeeeEeeeddddJdddddd44400333333333333333333333333333000bbgggcc0333333333422233300SSWWaWWWaWWWWUUUUXfXSS003333333333
555562222466600444ddeeeeeeeeeeeeeeEeeeedddddddFdd4440077777777777777777777777777000000000000077799999422266600SSWWaWWWaWWWWUUUUXfXSS005555555555
558562222466600444deeeeeeeeeeeeeeeEeeeeeddddddFdd4440099999999999999999999999890000hhhhhhh00009999999422266600SSWWaWWWaWWWWUUUUXfXSS005555555555
558562222466600444deeeeeeeeeeeeeeeEeeeeeedddddFdd444009999999999999999999999980000hiihhhhii0000999999422296600SSWWaWWWaWWWWUUUUXXXSS005555555555
558562222466600444eeeeeeeeeeeeeeeJEeeeeeeedddJddd4440099999999999999999999999000hhhiiiiiiiih000099999422296600SSWWaWWWaPPWWUUUUXXXSS005555555555
558662222466600444444444444444444J44444444444J444444009999999999999999999999900hhhhiiiiiiiihh00099999422296600SSWWaWWWaWWWWUUUUXXXSS005555555555
3333322224333004444444444444444444444444444444444444003333333333333333jjjk33300hhhhiiiiiiiihhh0033333422233300SSWWaWWWaWWWWUUUUXXXSS003333333333
5556622224660llllllllllllllllllllllllllllllllllllllllll077777777777777jjjk77700hhhhiiiiiiiiihmmmm9999422299600SSWWaWWWaWWWWUUUUXXXSS005555555555
5556622224660000000000000000000000000000000000000000000099899999999999jjj99900hhhhhiiiiiiiiihmmmm9999422299600SSWWaWWWaWWWWUUUUXXXSS005555555555
5566622224660000000000000000000000000000000000000000000099899999nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn999422299900SSWWaWWWaWWWWUUUUXXXSS005555555555
556662222466666666666666666669999899999999999999999999999989999nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn99222299900SSWWaWWWaWWWWUUUUXXXSS005555555555
5566622224666666666666666666999998999999999999999999999999899onnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn9222299900SSWWaWWWaWWWWUUUUXXXSS005555555555
3333322224333333333333333333333333333333333333333333333333333nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn222233300SSWWaWWWaWWWWUUUUXXXSS003333333333
5566622224666666666666666669999999999999999999999777777777777oooooooooooooooooooooooooooooooooooooooo222299900SSWWaWWWaWWWWUUUUXXXSS005555555555
5666622224666686666666666669999999999998999999999999999999999o44444444444444444444444444444444444444o222299900SSWWWWWWWWWUUUUUUXXXSS005555585555
5666622222666686666666666699999999999998999999999999999999999oppppppppppppppppppppppppppppppppppppppoo22299900SSWWWWWWUUUUUUUUUUUUSS005555585555
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqopprrrrrrppprrrrrrppprrrrrrppprrrrrrpppooqqqqqqqqqqWWqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqsqqqqqttttttttttstttttttttttutttstttttttttttvopprrrrrrppprrrrrrppprrrrrrppprrrrrrpppoottttttttttstttqqqqqqqqqqqqsqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqsqqqqqttttttttttsttttttttttttutttsttttttttttvvvpprrrrrrppprrrrrrppprrrrrrppprrrrrrpppottttttttttttstttqqqqqqwwwwwwwwwwqqqqqqqqqqq
qqqqqqqqqqqqqqsqqqqqtttttttttttstttttttttttxuttsttttttttttvvvvpprrrrrrppprrrrrrppprrrrrrppprrrrrrpppotttttttttttttstttqqqqqqqqqqqqsqqqqqqqqqqqqq
yyyyyyyyyyyyysyyyyyyyyyyyyyyyysyyyyyyyyyyyyzzzysyyyyyyyyyyyyyypprrrrrrppprrrrrrppprrrrrrppprrrrrrpppoyyyyyyyyyyyyysyyyyyyyyyyyyyyyysyyyyyyyyyyyy
qqqqqqqqqqqqqsqqqqqtttttttttttsttt!!!!!!!!!zzz!!!!!!!!!!!!!!!!!!!!!!!!!!!pppppppppppppppppppppppppppottttttttttttttstt###############qqqqqqqqqqq
qqqqqqqqqqqqsqqqqqtttttttttttsttt!!$$$$$$$$zzz$$$$$$$$$$$$$$$$$$$$!!!!!!!!ooooooooooooooooooooooooooottttttttttttttstttttqqqqqqqqqqqqsqqqqqqqqqq
qqqqqqqqqqqsqqqqqttttttttttttst!!!$$$$$$$$$zzz$$$$$$$$$$$$$$%%%%$$$!!!!!!!!ooooooooooooooooooooooooottttttttttttttttsttttqqqqqqqqqqqqqsqqqqqqqqq
qqqqqqqqqqqsqqqqttttttttttttst!!!$$$$$$$$&&zzz&&$$$$$$$$%%%%%%%%%$$$!!!!!!!!ooooooooooooooooooooooootttttttttttttttttsttttqqqqqqqqqqqqsqqqqqqqqq
yyyyyyyyyysyyyyyyyyyyyyyyyyy!!!!$$$$$$$$((((((((($$$$$$$%%%%%)*%%%$$$!!!!!!!!!yyysyyyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyyysyyyyyyyy
qqqqqqqqqsqqqqqttttttttttt!!!!!$$$$$$$$$$$$$$$$$$$$$$$$$$%%%%**%%%%$$$!!!!!!!!!vvvsvvvvvvvvvvvvvvvvtstttttttttttttttttstttttqqqqqqqqqqqqsqqqqqqq
qqqqqqqqsqqqqqttttttttttt!!!!!$$$$$$$$$$$$++++++$$$$$$$$$%%%%%%%%,,$$$$!!!!!!!!!vvsvvvvvvvvvvvvvvvvvsttttttttttttttttttstttttqqqqqqqqqqqqsqqqqqq
qqqqqqqqsqqqqtttttttttt!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!%%%,,,,,,,,!!!!!!!!!!!!!vsvvvvvvvvvvvvvvvvvtstttttttttttttttttsttttttqqqqqqqqqqqqsqqqqq
qqqqqqqsqqqqqttttttttt!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!,,,,,!!!!!!!!!!!!!!!!!!!svvvvvvvvvvvvvvvvvvsttttttttttttttttttstttttqqqqqqqqqqqqqsqqqq
qqqqqqsqqqqqtttttttttt------------------------------------------------------------.vvvvvvvvvvvvvvvvvvsttttttttttttttttttsttttttqqqqqqqqqqqqqsqqq
qqqqqsqqqqqtttttttttttttts/////////////////////////////////////////////////////......vvvvvvvvvvvvvvvvvsttttttttttttttttttsttttttqqqqqqqqqqqqsqqq
yyyyysyyyyyyyyyyyyyyyyyysy/////////////////////////////////////////////////////.......yyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyyyysyy
qqqqsqqqqqttttttttttttttst/////////////////////////////////////////////////////........vvvvvvvvvvvvvvvvsttttttttttttttttttstttttttqqqqqqqqqqqqsq
qqqsqqqqqttttttttttttttstt/////////////////////////////////////////////////////.......vvvvvvvvvvvvvvvvvstttttttttttttttttttstttttttqqqqqqqqqqqqs
qqsqqqqqtttttttttttttttstt:::::::::::::::::::::::::::::::::::::::::::::::::::::.......vvvvvvvvvvvvvvvvvsttttttttttttttttttttsttttttqqqqqqqqqqqqq
qqsqqqqtttttttttttttttsttt////;;;;//////////////////////////////////////;;;;///......vvvvvvvvvvvvvvvvvvvstttttttttttttttttttstttttttqqqqqqqqqqqq
qsqqqqqtttttttttttttttsttt////;;;;//////////////////////////////////////;;;;///......vvvvvvvvvvvvvvvvvvvsttttttttttttttttttttstttttttqqqqqqqqqqq
sqqqqqtttttttttttttttstttt////;;;;//////////////////////////////////////;;;;///.....svvvvvvvvvvvvvvvvvvvvsttttttttttttttttttttstttttttqqqqqqqqqq
sqqqqttttttttttttttttstttt////;;;;//////////////////////////////////////;;;;///.....svvvvvvvvvvvvvvvvvvvvsttttttttttttttttttttsttttttttqqqqqqqqq
yyyyyyyyyyyyyyyyyyyysyyyyy////;;;;//////////////////////////////////////;;;;///....ysyyyyyyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyyyyyyysyyyyyyyyyyyyyyyy
```

</details>
