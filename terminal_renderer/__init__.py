"""Encode RGB pixel frames as ANSI truecolor terminal cells."""

from collections.abc import Sequence

RGB = tuple[int, int, int]
RESET = "\x1b[0m"


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _valid_rgb(color: object) -> bool:
    return (
        _is_sequence(color)
        and len(color) == 3
        and all(type(channel) is int and 0 <= channel <= 255 for channel in color)
    )


def encode_frame(
    rows: Sequence[Sequence[RGB]], *, pad: RGB = (0, 0, 0)
) -> str:
    """Return half-block rows with a color reset at the end of each row."""
    if not _is_sequence(rows) or not rows or not _is_sequence(rows[0]) or not rows[0]:
        raise ValueError("frame must be a nonempty rectangle")
    width = len(rows[0])
    for row in rows:
        if not _is_sequence(row) or len(row) != width:
            raise ValueError("frame rows must all have the same width")
        if not all(_valid_rgb(color) for color in row):
            raise ValueError("pixels must be RGB triples of integers from 0 to 255")
    if not _valid_rgb(pad):
        raise ValueError("pad must be an RGB triple of integers from 0 to 255")

    encoded = []
    for y in range(0, len(rows), 2):
        upper = rows[y]
        lower = rows[y + 1] if y + 1 < len(rows) else [pad] * width
        active = None
        cells = []
        for top, bottom in zip(upper, lower):
            pair = tuple(top), tuple(bottom)
            if pair != active:
                r, g, b = top
                lower_r, lower_g, lower_b = bottom
                cells.append(f"\x1b[38;2;{r};{g};{b};48;2;{lower_r};{lower_g};{lower_b}m")
                active = pair
            cells.append("▀")
        encoded.append("".join(cells) + RESET)
    return "\n".join(encoded)
