import re
import unittest

from terminal_renderer.cli import fit_frame, tavern
from terminal_renderer import RESET, encode_frame

SGR = re.compile(r"\x1b\[[0-9;]*m")
BLACK = (0, 0, 0)


class EncodeFrameTests(unittest.TestCase):
    def test_upper_foreground_and_lower_background_keep_rgb_order(self):
        self.assertEqual(
            encode_frame([[(1, 2, 3)], [(4, 5, 6)]]),
            "\x1b[38;2;1;2;3;48;2;4;5;6m▀" + RESET,
        )

    def test_odd_height_uses_custom_pad(self):
        self.assertEqual(
            encode_frame([[(10, 20, 30)]], pad=(40, 50, 60)),
            "\x1b[38;2;10;20;30;48;2;40;50;60m▀" + RESET,
        )

    def test_dimensions_reset_and_no_trailing_newline(self):
        output = encode_frame([[BLACK] * 5] * 3)
        self.assertFalse(output.endswith("\n"))
        self.assertTrue(all(row.endswith(RESET) for row in output.splitlines()))
        self.assertEqual(SGR.sub("", output).splitlines(), ["▀" * 5] * 2)

    def test_reuses_color_pair_only_within_a_row(self):
        red = (255, 0, 0)
        output = encode_frame([[BLACK, BLACK, red, BLACK, BLACK]] * 4)
        for row in output.splitlines():
            self.assertEqual(row.count("\x1b[38;2;"), 3)
            self.assertIn("m▀▀", row)

    def test_rejects_invalid_input(self):
        for frame in (None, [], [[]], [[BLACK], [BLACK, BLACK]], [[(0, 0)]],
                      [[(0, 0, 256)]], [[(-1, 0, 0)]], [[(0, 0, 0.5)]],
                      [[(False, 0, 0)]], ["rgb"]):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                encode_frame(frame)
        with self.assertRaises(ValueError):
            encode_frame([[BLACK]], pad=(0, 0, 999))

    def test_tavern_fixture_dimensions_and_palette(self):
        pixels = tavern().background
        self.assertEqual((len(pixels[0]), len(pixels)), (144, 80))
        self.assertEqual(len({color for row in pixels for color in row}), 77)
        self.assertEqual(
            SGR.sub("", encode_frame(pixels)).splitlines(), ["▀" * 144] * 40,
        )

    def test_fit_respects_width_and_height_constraints(self):
        pixels = [list(row) for row in tavern().background]
        self.assertIs(fit_frame(pixels, 144, 40), pixels)
        self.assertEqual(len(fit_frame(pixels, 72, 40)[0]), 72)
        smaller = fit_frame(pixels, 144, 10)
        self.assertEqual((len(smaller[0]), len(smaller)), (36, 20))
