"""Scene data, pixel art, and deterministic object interactions."""

from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
import re
from typing import TypeAlias

from . import RGB

WIDTH, HEIGHT = 144, 80
Bounds: TypeAlias = tuple[int, int, int, int]
Frame: TypeAlias = tuple[tuple[RGB, ...], ...]
Span: TypeAlias = tuple[int, int, int, RGB]
BLACK = (0, 0, 0)


@dataclass(frozen=True)
class Target:
    name: str
    bounds: Bounds
    text: str
    requires: str | None = None
    blocked: str = ""
    art: tuple[Span, ...] = ()
    active_art: tuple[Span, ...] | None = None
    revisit: str = ""


@dataclass(frozen=True)
class Scene:
    title: str
    intro: str
    background: Frame
    targets: tuple[Target, ...]
    flicker: tuple[Span, ...] = ()


@dataclass
class PlayState:
    scene: Scene
    selected: int | None = None
    used: set[str] = field(default_factory=set)
    dialogue: str = field(init=False)

    def __post_init__(self) -> None:
        self.dialogue = self.scene.intro

    def interact(self, index: int) -> None:
        target = self.scene.targets[index]
        self.selected = index
        if target.name in self.used:
            self.dialogue = target.revisit or target.text
        elif target.requires and target.requires not in self.used:
            self.dialogue = target.blocked
        else:
            self.used.add(target.name)
            self.dialogue = target.text

    def pixels(self, phase: int) -> list[list[RGB]]:
        pixels = [list(row) for row in self.scene.background]
        for target in self.scene.targets:
            art = target.art
            if target.active_art is not None and target.name in self.used:
                art = target.active_art
            paint(pixels, art)
        if phase:
            paint(pixels, self.scene.flicker)
        return pixels


def load_indexed_frame(path: Path) -> Frame:
    """Decode the indexed palette and immutable RGB pixels of a text fixture."""
    dimensions, symbols, colors, *grid = path.read_text(encoding="utf-8").splitlines()
    width, height = map(int, dimensions.split())
    palette = dict(zip(symbols, map(_rgb, colors.split()), strict=True))
    if (
        width < 1 or height < 1 or len(palette) != len(symbols)
        or len(grid) != height or any(len(row) != width for row in grid)
    ):
        raise ValueError("invalid indexed framebuffer dimensions or palette")
    try:
        return tuple(tuple(palette[symbol] for symbol in row) for row in grid)
    except KeyError as error:
        raise ValueError(f"unknown fixture color {error}") from error


def paint(pixels: list[list[RGB]], spans: tuple[Span, ...]) -> None:
    for y, left, right, color in spans:
        pixels[y][left:right] = [color] * (right - left)


def parse_scene(data: object, *, allow_static: bool = False) -> Scene:
    """Validate a scene JSON document and compile its shapes to RGB pixels."""
    if not isinstance(data, dict):
        raise ValueError("scene must be a JSON object")
    version = data.get("version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("scene version must be 1 or 2")
    title = _text(data.get("title"), "title", 60)
    intro = _text(data.get("intro"), "intro", 240)
    raw_palette = data.get("palette")
    if not isinstance(raw_palette, dict) or not 1 <= len(raw_palette) <= 32:
        raise ValueError("palette must be an object with 1 to 32 named colors")
    palette = {name: _rgb(hex_color) for name, hex_color in raw_palette.items()}
    canvas = (0, 0, WIDTH, HEIGHT)
    pixels = [[BLACK] * WIDTH for _ in range(HEIGHT)]
    paint(pixels, _shapes(data.get("background"), palette, canvas, "background", 64))

    objects = data.get("objects")
    minimum_objects = 0 if allow_static else 1
    if not isinstance(objects, list) or not minimum_objects <= len(objects) <= 5:
        raise ValueError(f"objects must contain {minimum_objects} to 5 interactable objects")
    targets = []
    for index, obj in enumerate(objects, start=1):
        label = f"object {index}"
        if not isinstance(obj, dict):
            raise ValueError(f"{label} must be a JSON object")
        name = _text(obj.get("name"), f"{label} name", 24)
        bounds = _rect(obj.get("bounds"), canvas, f"{name} bounds")
        if version == 2:
            for other in targets:
                if _overlap(bounds, other.bounds):
                    raise ValueError(f"{name} bounds overlap {other.name}")
        art = _object_art(obj.get("art"), palette, bounds, f"{name} art", version)
        text = _text(obj.get("text"), f"{name} interaction", 240)
        requires = obj.get("requires")
        blocked = ""
        if requires is not None:
            requires = _text(requires, f"{name} prerequisite", 24)
            blocked = _text(obj.get("blocked"), f"{name} blocked interaction", 240)
        active_art = None
        if version == 1 and "after" in obj:
            active_art = art + _object_art(obj["after"], palette, bounds, f"{name} after art", version)
        if version == 2:
            if "after" in obj:
                raise ValueError(f"{name} must use active_art for its full replacement art")
            if "active_art" in obj:
                active_art = _object_art(obj["active_art"], palette, bounds, f"{name} active art", version)
        revisit = ""
        if "revisit" in obj:
            revisit = _text(obj["revisit"], f"{name} revisit", 240)
        elif active_art is not None:
            revisit = f"You have already interacted with the {name.lower()}."
        targets.append(Target(
            name, bounds, text, requires=requires, blocked=blocked,
            art=art, active_art=active_art, revisit=revisit,
        ))

    prerequisites = {target.name: target.requires for target in targets}
    if len({name.casefold() for name in prerequisites}) != len(targets):
        raise ValueError("object names must be unique")
    for name, requirement in prerequisites.items():
        seen = {name}
        while requirement is not None:
            if requirement in seen or requirement not in prerequisites:
                raise ValueError(f"{name} has a cyclic or unknown prerequisite: {requirement}")
            seen.add(requirement)
            requirement = prerequisites[requirement]

    return Scene(title, intro, tuple(map(tuple, pixels)), tuple(targets))


def _overlap(first: Bounds, second: Bounds) -> bool:
    x, y, width, height = first
    other_x, other_y, other_width, other_height = second
    return (
        x < other_x + other_width and other_x < x + width
        and y < other_y + other_height and other_y < y + height
    )


def _object_art(value: object, palette: dict[str, RGB], bounds: Bounds,
                label: str, version: int) -> tuple[Span, ...]:
    if version == 1:
        return _shapes(value, palette, bounds, label, 24)
    x, y, width, height = bounds
    spans = _shapes(value, palette, (0, 0, width, height), label, 24)
    return tuple((row + y, left + x, right + x, color) for row, left, right, color in spans)


def _text(value: object, label: str, max_length: int) -> str:
    if (
        not isinstance(value, str) or not value.strip()
        or len(value) > max_length or not value.isascii() or not value.isprintable()
    ):
        raise ValueError(f"{label} must be 1 to {max_length} printable ASCII characters")
    return value.strip()


def _rgb(value: object) -> RGB:
    if not isinstance(value, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", value):
        raise ValueError("palette colors must be six-digit RGB hex strings")
    hex_color = value.lstrip("#")
    return int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)


def _rect(value: object, bounds: Bounds, label: str) -> Bounds:
    if (
        not isinstance(value, list) or len(value) != 4
        or any(type(coordinate) is not int for coordinate in value)
    ):
        raise ValueError(f"{label} must contain four integers [x, y, width, height]")
    x, y, width, height = value
    left, top, area_width, area_height = bounds
    if not (
        width > 0 and height > 0 and left <= x <= x + width <= left + area_width
        and top <= y <= y + height <= top + area_height
    ):
        raise ValueError(f"{label} must be within its drawing bounds")
    return x, y, width, height


def _shapes(value: object, palette: dict[str, RGB], bounds: Bounds,
            label: str, maximum: int) -> tuple[Span, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array of shapes")
    if not 1 <= len(value) <= maximum:
        raise ValueError(f"{label} has {len(value)} shapes. Expected 1 to {maximum}")
    spans = []
    for index, shape in enumerate(value, start=1):
        item = f"{label} shape {index}"
        if not isinstance(shape, list) or len(shape) < 3:
            raise ValueError(f"{item} must be an array with a type, color, and coordinates")
        kind, name, *coordinates = shape
        if not isinstance(name, str) or name not in palette:
            raise ValueError(f"{item} names an undeclared palette color: {name!r}")
        color = palette[name]
        if kind == "rect":
            x, y, width, height = _rect(coordinates, bounds, item)
            spans.extend((row, x, x + width, color) for row in range(y, y + height))
        elif kind == "poly":
            spans.extend(_polygon(coordinates, bounds, color, item))
        else:
            raise ValueError(f"{item} type must be rect or poly")
    return tuple(spans)


def _polygon(points: list, bounds: Bounds, color: RGB, label: str) -> list[Span]:
    if any(
        not isinstance(point, list) or len(point) != 2
        or any(type(coordinate) is not int for coordinate in point)
        for point in points
    ):
        raise ValueError(f"{label} polygon vertices must be [x, y] integer pairs")
    if not 3 <= len(points) <= 12:
        raise ValueError(f"{label} polygon has {len(points)} vertices. Expected 3 to 12")
    left, top, width, height = bounds
    if any(not (left <= x <= left + width and top <= y <= top + height) for x, y in points):
        raise ValueError(f"{label} polygon vertices must be within its drawing bounds")
    edges = list(zip(points, points[1:] + points[:1]))
    spans = []
    for y in range(min(point[1] for point in points), max(point[1] for point in points)):
        mid = y + 0.5
        cuts = sorted(
            x1 + (mid - y1) * (x2 - x1) / (y2 - y1)
            for (x1, y1), (x2, y2) in edges
            if min(y1, y2) <= mid < max(y1, y2)
        )
        spans.extend(
            (y, ceil(start - 0.5), ceil(end - 0.5), color)
            for start, end in zip(cuts[::2], cuts[1::2])
            if ceil(start - 0.5) < ceil(end - 0.5)
        )
    if not spans:
        raise ValueError(f"{label} polygon must cover at least one pixel")
    return spans
