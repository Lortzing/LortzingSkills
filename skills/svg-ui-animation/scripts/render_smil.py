#!/usr/bin/env python3
"""Sample a deliberately small SVG/SMIL subset and render PNGs without a browser.

Requires lxml and system librsvg (2.46+), cairo, and gobject. Fontconfig is needed
only for --font. Supported tracks: numeric opacity and translate/scale/rotate;
linear/discrete/spline; numeric clock offsets; repeatCount 1 or indefinite.
Unsupported animations and active/external content are rejected, never stripped.
"""
from __future__ import annotations

import argparse
import base64
import bisect
import copy
import ctypes as C
import ctypes.util
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sys

try:
    from lxml import etree
except ImportError:
    raise SystemExit("Missing Python dependency: install lxml (python -m pip install lxml).")

NS = "http://www.w3.org/2000/svg"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
CLOCK = re.compile(rf"^({NUMBER})(ms|s)?$")
LENGTH = re.compile(rf"^({NUMBER})(px)?$")
RASTER_DATA = re.compile(r"^data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+$")


class AnimationError(ValueError):
    """The input cannot be sampled faithfully by this restricted renderer."""


def finite(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AnimationError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise AnimationError(f"{label} must be a finite number")
    return result


def positive(value, label):
    result = finite(value, label)
    if result <= 0:
        raise AnimationError(f"{label} must be greater than zero")
    return result


def seconds(value, label="clock value"):
    match = CLOCK.fullmatch(str(value).strip())
    if not match:
        raise AnimationError(f"Unsupported {label}: {value!r}; use a numeric offset such as 1.2s or 250ms")
    result = finite(match.group(1), label)
    return result / 1000 if match.group(2) == "ms" else result


def numbers(value, label):
    fields = re.split(r"[\s,]+", value.strip())
    if not fields or any(not re.fullmatch(NUMBER, field) for field in fields):
        raise AnimationError(f"{label} must contain numeric values, got {value!r}")
    return tuple(finite(field, label) for field in fields)


def local_name(node):
    return etree.QName(node).localname if isinstance(node.tag, str) else ""


def ensure_safe_output(path):
    """Reject output symlinks, including dangling links and linked ancestors."""
    absolute = Path(path).absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink():
            raise AnimationError(f"Refusing to write through an output symlink: {candidate}")


def check_url(value):
    if "\\" in value:
        raise AnimationError("CSS escape sequences are unsupported; use literal presentation attributes")
    for match in re.finditer(r"url\s*\((.*?)\)", value, re.I | re.S):
        target = match.group(1).strip().strip("\"'")
        if not target.startswith("#"):
            raise AnimationError("External CSS/SVG url() resources are not supported; inline assets first")


def embedded_raster(value):
    if not RASTER_DATA.fullmatch(value):
        return False
    header, encoded = value.split(",", 1)
    try:
        data = base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
    except ValueError:
        return False
    mime = header.split(";", 1)[0]
    return ((mime == "data:image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
            or (mime == "data:image/jpeg" and data.startswith(b"\xff\xd8\xff"))
            or (mime == "data:image/gif" and data[:6] in {b"GIF87a", b"GIF89a"})
            or (mime == "data:image/webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP"))


def dimensions(root):
    viewbox = root.get("viewBox")
    box = numbers(viewbox, "viewBox") if viewbox else None
    if box is not None and (len(box) != 4 or box[2] <= 0 or box[3] <= 0):
        raise AnimationError("viewBox must contain min-x, min-y, positive width and height")

    def length(name):
        value = root.get(name)
        if value is None or value.strip().endswith("%"):
            return None
        match = LENGTH.fullmatch(value.strip())
        if not match:
            raise AnimationError(f"Root {name} must be unitless or px; use viewBox for a responsive canvas")
        return positive(match.group(1), name)

    width, height = length("width"), length("height")
    if width is None and height is None and box:
        width, height = box[2:]
    elif width is None and height is not None and box:
        width = height * box[2] / box[3]
    elif height is None and width is not None and box:
        height = width * box[3] / box[2]
    if width is None or height is None:
        raise AnimationError("Specify numeric width and height, or a valid viewBox")
    return width, height


def spline_fraction(u, controls):
    x1, y1, x2, y2 = controls

    def component(t, a, b):
        return 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3

    low, high = 0.0, 1.0
    for _ in range(28):
        middle = (low + high) / 2
        if component(middle, x1, x2) < u:
            low = middle
        else:
            high = middle
    return component((low + high) / 2, y1, y2)


@dataclass
class Track:
    path: str
    attribute: str
    transform: str | None
    begin: float
    duration: float
    repeat: str
    fill: str
    mode: str
    values: list[tuple[float, ...]]
    times: list[float]
    splines: list[tuple[float, ...]]

    def sample(self, time):
        elapsed = time - self.begin
        if elapsed < 0:
            return None
        if self.repeat == "indefinite":
            progress = (elapsed % self.duration) / self.duration
        elif elapsed >= self.duration:
            if self.fill != "freeze":
                return None
            progress = 1.0
        else:
            progress = elapsed / self.duration
        index = min(bisect.bisect_right(self.times, progress) - 1, len(self.values) - 1)
        if self.mode == "discrete" or index == len(self.values) - 1:
            result = self.values[index]
        else:
            span = self.times[index + 1] - self.times[index]
            u = (progress - self.times[index]) / span if span else 1.0
            if self.mode == "spline":
                u = spline_fraction(u, self.splines[index])
            result = tuple(a + (b - a) * u for a, b in zip(self.values[index], self.values[index + 1]))
        value = " ".join(f"{v:.9g}" for v in result)
        return f"{self.transform}({value})" if self.transform else value


def parse_track(node, path):
    tag = local_name(node)
    allowed = {"id", "attributeName", "attributeType", "type", "values", "from", "to", "keyTimes",
               "calcMode", "keySplines", "dur", "begin", "repeatCount", "fill", "additive", "accumulate"}
    unexpected = set(node.attrib) - allowed
    if unexpected:
        raise AnimationError(f"Unsupported animation attributes at {path}: {', '.join(sorted(unexpected))}")
    if len(node):
        raise AnimationError(f"Nested animation content is unsupported at {path}")
    if node.get("additive", "replace") != "replace" or node.get("accumulate", "none") != "none":
        raise AnimationError("Additive/accumulated tracks are unsupported; use nested SVG groups")
    if node.get("attributeType", "auto") not in {"auto", "XML"}:
        raise AnimationError("Use SVG presentation attributes; explicit CSS animation targets are unsupported")
    attr = node.get("attributeName")
    transform = None
    if tag == "animate":
        if attr != "opacity" or "type" in node.attrib:
            raise AnimationError("<animate> supports only numeric opacity in this renderer")
    else:
        transform = node.get("type")
        if attr != "transform" or transform not in {"translate", "scale", "rotate"}:
            raise AnimationError("<animateTransform> supports only translate, scale, and rotate")
    begin = seconds(node.get("begin", "0s"), "begin")
    duration = positive(seconds(node.get("dur", ""), "dur"), "dur")
    repeat = node.get("repeatCount", "1")
    if repeat not in {"1", "indefinite"}:
        raise AnimationError("Only repeatCount='1' or 'indefinite' is supported")
    fill = node.get("fill", "remove")
    if fill not in {"freeze", "remove"}:
        raise AnimationError("Animation fill must be freeze or remove")
    mode = node.get("calcMode", "linear")
    if mode not in {"linear", "discrete", "spline"}:
        raise AnimationError("Only linear, discrete, and spline interpolation are supported")
    if "values" in node.attrib:
        if "from" in node.attrib or "to" in node.attrib:
            raise AnimationError("Use either values or from/to, not both")
        raw_values = node.get("values").split(";")
    elif "from" in node.attrib and "to" in node.attrib:
        raw_values = [node.get("from"), node.get("to")]
    else:
        raise AnimationError("Each track requires values or an explicit from/to pair")
    if len(raw_values) < 2:
        raise AnimationError("Provide at least two animation values")
    values = []
    for raw in raw_values:
        val = numbers(raw, "animation values")
        if transform in {"translate", "scale"} and len(val) == 1:
            val = (val[0], 0.0 if transform == "translate" else val[0])
        if transform == "rotate" and len(val) == 1:
            val = (val[0], 0.0, 0.0)
        expected = 3 if transform == "rotate" else 2 if transform else 1
        if len(val) != expected:
            raise AnimationError(f"Wrong numeric value count for {transform or attr}: {raw!r}")
        values.append(val)
    if "keyTimes" in node.attrib:
        times = [finite(v, "keyTimes") for v in node.get("keyTimes").split(";")]
    else:
        divisor = len(values) if mode == "discrete" else len(values) - 1
        times = [i / divisor for i in range(len(values))]
    if (len(times) != len(values) or times[0] != 0 or any(t < 0 or t > 1 for t in times)
            or any(a > b for a, b in zip(times, times[1:])) or (mode != "discrete" and times[-1] != 1)):
        raise AnimationError("keyTimes must match values, be ordered within 0..1, start at 0, and end at 1 for interpolation")
    splines = []
    if mode == "spline":
        splines = [numbers(v, "keySplines") for v in node.get("keySplines", "").split(";")]
        if len(splines) != len(values) - 1 or any(len(s) != 4 or any(v < 0 or v > 1 for v in s) for s in splines):
            raise AnimationError("keySplines requires one four-number curve in 0..1 for each interval")
    elif "keySplines" in node.attrib:
        raise AnimationError("keySplines requires calcMode='spline'")
    return Track(path, attr, transform, begin, duration, repeat, fill, mode, values, times, splines)


@dataclass
class Document:
    root: object
    width: float
    height: float
    tracks: list[Track]

    def frame(self, time, background=None):
        time = finite(time, "time")
        if time < 0:
            raise AnimationError("time must be nonnegative")
        root = copy.deepcopy(self.root)
        # Resolve paths before removing siblings, so indexed element paths stay valid.
        nodes = [root.find(track.path) for track in self.tracks]
        for track, node in zip(self.tracks, nodes):
            parent = node.getparent()
            value = track.sample(time)
            if value is not None:
                parent.set(track.attribute, value)
            parent.remove(node)
        if background:
            check_url(background)
            rect = etree.Element(f"{{{NS}}}rect", width="100%", height="100%", fill=background)
            box = root.get("viewBox")
            if box:
                x, y, w, h = numbers(box, "viewBox")
                rect.attrib.update({"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
            root.insert(0, rect)
        root.set("width", f"{self.width:.9g}")
        root.set("height", f"{self.height:.9g}")
        return etree.tostring(root)


def load_svg(path):
    raw = Path(path).read_bytes()
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise AnimationError("DTD/entity declarations are not allowed")
    try:
        root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
    except etree.XMLSyntaxError as exc:
        raise AnimationError(f"Invalid SVG XML: {exc}") from exc
    if root.tag != f"{{{NS}}}svg":
        raise AnimationError("The root must be an SVG element with xmlns='http://www.w3.org/2000/svg'")
    if root.getroottree().xpath("//processing-instruction()"):
        raise AnimationError("XML processing instructions are not supported")
    tracks, targets = [], set()
    for node in root.iter():
        if isinstance(node, etree._Entity):
            raise AnimationError("Entity references are not allowed")
        tag = local_name(node)
        if not tag:
            continue
        if tag in {"script", "foreignObject", "style", "set", "animateMotion", "animateColor", "discard"}:
            raise AnimationError(f"Unsupported <{tag}>; use static presentation attributes and supported SMIL tracks")
        if tag.startswith("animate") and tag not in {"animate", "animateTransform"}:
            raise AnimationError(f"Unsupported animation element <{tag}>")
        for key, value in node.attrib.items():
            name = etree.QName(key).localname
            if name.lower().startswith("on") or name == "base":
                raise AnimationError(f"Event handlers and base URLs are not allowed: {name}")
            if name == "href" and not (value.startswith("#") or (tag == "image" and embedded_raster(value))):
                raise AnimationError("External href resources are not allowed; use local fragment references or embedded raster images")
            if name == "style":
                raise AnimationError("Inline CSS is unsupported; use SVG presentation attributes")
            check_url(value)
        if tag in {"animate", "animateTransform"}:
            path = root.getroottree().getelementpath(node)
            track = parse_track(node, path)
            parent = node.getparent()
            if parent is None:
                raise AnimationError("An animation needs a target parent")
            target = (root.getroottree().getelementpath(parent), track.attribute)
            if target in targets:
                raise AnimationError("Multiple tracks on one target attribute are unsupported; use nested groups")
            targets.add(target)
            tracks.append(track)
    width, height = dimensions(root)
    return Document(root, width, height, tracks)


def native_library(name):
    path = ctypes.util.find_library(name)
    if not path:
        raise AnimationError(f"Missing native library {name}. Install librsvg/cairo/fontconfig (macOS: brew install librsvg; Debian/Ubuntu: librsvg2-2 libcairo2 fontconfig).")
    try:
        return C.CDLL(path)
    except OSError as exc:
        raise AnimationError(f"Cannot load {name}: {exc}") from exc


class Rectangle(C.Structure):
    _fields_ = [(name, C.c_double) for name in ("x", "y", "width", "height")]


class Renderer:
    def __init__(self, fonts=()):
        if fonts:
            fc = native_library("fontconfig")
            fc.FcConfigGetCurrent.restype = C.c_void_p
            fc.FcConfigAppFontAddFile.argtypes = [C.c_void_p, C.c_char_p]
            fc.FcConfigAppFontAddFile.restype = C.c_int
            for font in fonts:
                path = Path(font).resolve(strict=True)
                if not path.is_file() or not fc.FcConfigAppFontAddFile(fc.FcConfigGetCurrent(), str(path).encode()):
                    raise AnimationError(f"Cannot register font: {path}")
        self.r = native_library("rsvg-2")
        self.c = native_library("cairo")
        self.g = native_library("gobject-2.0")
        try:
            self.r.rsvg_handle_render_document.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Rectangle), C.c_void_p]
        except AttributeError as exc:
            raise AnimationError("librsvg 2.46 or newer is required") from exc
        self.r.rsvg_handle_render_document.restype = C.c_int
        self.r.rsvg_handle_new_from_data.argtypes = [C.c_char_p, C.c_size_t, C.c_void_p]
        self.r.rsvg_handle_new_from_data.restype = C.c_void_p
        self.c.cairo_image_surface_create.argtypes = [C.c_int, C.c_int, C.c_int]
        self.c.cairo_image_surface_create.restype = C.c_void_p
        self.c.cairo_surface_status.argtypes = [C.c_void_p]
        self.c.cairo_surface_status.restype = C.c_int
        self.c.cairo_create.argtypes = [C.c_void_p]
        self.c.cairo_create.restype = C.c_void_p
        self.c.cairo_surface_write_to_png.argtypes = [C.c_void_p, C.c_char_p]
        self.c.cairo_surface_write_to_png.restype = C.c_int
        self.c.cairo_destroy.argtypes = [C.c_void_p]
        self.c.cairo_surface_destroy.argtypes = [C.c_void_p]
        self.g.g_object_unref.argtypes = [C.c_void_p]

    def png(self, svg, output, width, height):
        ensure_safe_output(output)
        handle = self.r.rsvg_handle_new_from_data(svg, len(svg), None)
        if not handle:
            raise AnimationError("librsvg rejected the sampled SVG frame")
        surface = context = None
        try:
            surface = self.c.cairo_image_surface_create(0, width, height)
            if self.c.cairo_surface_status(surface):
                raise AnimationError("Cairo could not allocate the requested image dimensions")
            context = self.c.cairo_create(surface)
            viewport = Rectangle(0, 0, width, height)
            if not self.r.rsvg_handle_render_document(handle, context, C.byref(viewport), None):
                raise AnimationError("librsvg could not render the sampled frame")
            if self.c.cairo_surface_write_to_png(surface, str(output).encode()):
                raise AnimationError(f"Could not write PNG: {output}")
        finally:
            if context:
                self.c.cairo_destroy(context)
            if surface:
                self.c.cairo_surface_destroy(surface)
            self.g.g_object_unref(handle)


def pixel_dimensions(document, scale):
    scale = positive(scale, "scale")
    dims = tuple(round(value * scale) for value in (document.width, document.height))
    if min(dims) < 1 or max(dims) > 32767:
        raise AnimationError("Scaled image dimensions must be between 1 and 32767 pixels")
    return dims


def frame_count(duration, fps):
    duration = positive(duration, "duration")
    if not isinstance(fps, int) or fps <= 0:
        raise AnimationError("fps must be a positive integer")
    if duration * fps < 1:
        raise AnimationError("duration must contain at least one frame at the requested fps")
    return math.ceil(duration * fps - 1e-9)


def render_frames(document, output, duration, fps=30, scale=1, fonts=(), background=None, overwrite=False):
    count = frame_count(duration, fps)
    width, height = pixel_dimensions(document, scale)
    output = Path(output)
    ensure_safe_output(output)
    if output.exists():
        entries = list(output.iterdir())
        if entries and not overwrite:
            raise AnimationError(f"Frame directory is not empty: {output}; use --overwrite deliberately")
        if any(p.is_symlink() or not p.is_file() or not re.fullmatch(r"frame_\d{6}\.png", p.name) for p in entries):
            raise AnimationError("Refusing to clear a frame directory containing unrelated files")
    else:
        entries = []
    renderer = Renderer(fonts)
    output.mkdir(parents=True, exist_ok=True)
    for path in entries:
        path.unlink()
    for index in range(count):
        renderer.png(document.frame(index / fps, background), output / f"frame_{index:06d}.png", width, height)
    return {"frames": count, "width": width, "height": height, "fps": fps, "duration": count / fps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    parser.add_argument("output", type=Path, help="PNG filename or frame directory when --duration is used")
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--time", type=float, help="Snapshot time in seconds (default: 0)")
    timing.add_argument("--duration", type=float, help="Render a frame sequence from time zero")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--font", type=Path, action="append", default=[], help="Local font file; may be repeated")
    parser.add_argument("--background", help="Optional static SVG background color")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        document = load_svg(args.svg)
        ensure_safe_output(args.output)
        if args.svg.resolve() == args.output.resolve():
            raise AnimationError("Input and output must be different paths")
        if args.duration is not None:
            result = render_frames(document, args.output, args.duration, args.fps, args.scale,
                                   args.font, args.background, args.overwrite)
            print(f"Rendered {result['frames']} frames, {result['width']}x{result['height']}, {result['duration']:.6g}s at {args.fps} fps")
        else:
            if args.output.suffix.lower() != ".png":
                raise AnimationError("A snapshot output must end in .png")
            if args.output.exists() and not args.overwrite:
                raise AnimationError(f"Output exists: {args.output}; use --overwrite deliberately")
            width, height = pixel_dimensions(document, args.scale)
            sampled = document.frame(args.time or 0, args.background)
            renderer = Renderer(args.font)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            renderer.png(sampled, args.output, width, height)
            print(f"Rendered {args.output} ({width}x{height})")
    except (AnimationError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
