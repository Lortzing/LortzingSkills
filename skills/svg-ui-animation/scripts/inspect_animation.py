#!/usr/bin/env python3
"""Inspect local SVG/HTML/ZIP animation references without executing or fetching them."""
from __future__ import annotations

import argparse
import html.entities
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import zipfile

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].split(":")[-1]


def xml_entities(raw: str) -> str:
    def replace(match):
        name = match.group(1)
        if name in {"amp", "lt", "gt", "quot", "apos"}:
            return match.group(0)
        number = html.entities.name2codepoint.get(name)
        return f"&#{number};" if number is not None else match.group(0)
    return re.sub(r"&([A-Za-z][A-Za-z0-9]+);", replace, raw)


class PageInspector(HTMLParser):
    """Retain exact SVG source slices; HTMLParser otherwise lowercases SVG names."""
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.stack = []
        self.svg_start = None
        self.svg_depth = 0
        self.svg_in_article = False
        self.svgs = []
        self.media = []
        self.has_article = False

    def absolute_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def in_article(self):
        return any(is_article for _, is_article in self.stack)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        is_article = attrs.get("id") == "js_content"
        self.has_article |= is_article
        inside = self.in_article() or is_article
        if tag == "svg":
            if self.svg_depth == 0:
                self.svg_start = self.absolute_offset()
                self.svg_in_article = inside
            self.svg_depth += 1
        if tag in {"img", "video", "source", "iframe", "mp-common-videosnap"}:
            src = attrs.get("data-src") or attrs.get("src") or ""
            is_gif = attrs.get("data-type", "").lower() == "gif" or bool(re.search(r"(?:\.gif(?:[?#]|$)|wx_fmt=gif|^data:image/gif)", src, re.I))
            if tag != "img" or is_gif:
                self.media.append({"tag": tag, "gif_hint": is_gif, "resource": summarize_resource(src), "in_article": inside})
        if tag not in VOID_TAGS:
            self.stack.append((tag, is_article))

    def handle_startendtag(self, tag, attrs):
        if tag == "svg":
            self.svgs.append((self.get_starttag_text(), self.in_article()))
        elif tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1
            if self.svg_depth == 0:
                end = self.source.find(">", self.absolute_offset()) + 1
                self.svgs.append((self.source[self.svg_start:end], self.svg_in_article))
                self.svg_start = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def summarize_resource(value: str):
    value = value.strip()
    if not value:
        return {"kind": "empty"}
    if value.startswith("#"):
        return {"kind": "fragment"}
    if value.lower().startswith("data:"):
        return {"kind": "embedded", "media_type": value[5:].split(";", 1)[0].split(",", 1)[0]}
    try:
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            # Keep no path, query, credentials, or token-bearing fragment.
            return {"kind": "external", "scheme": parsed.scheme or "https", "host": parsed.hostname or ""}
    except ValueError:
        return {"kind": "external", "scheme": "unknown", "host": "unparseable"}
    return {"kind": "relative-file"}


def inspect_svg(raw: str):
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise ValueError("SVG declarations containing DOCTYPE/ENTITY are not supported")
    root = ET.fromstring(xml_entities(raw))
    if local_name(root.tag).lower() != "svg":
        raise ValueError("Expected an SVG root element")
    counts = {"animate": 0, "animateTransform": 0, "animateMotion": 0, "set": 0}
    canonical = {name.lower(): name for name in counts}
    tracks = []
    resources = []
    risks = {"script_elements": 0, "foreign_object_elements": 0, "event_attributes": 0, "style_elements": 0}
    for node in root.iter():
        tag = local_name(node.tag)
        lower = tag.lower()
        if lower in canonical:
            counts[canonical[lower]] += 1
            tracks.append({key: node.get(key) for key in ("attributeName", "type", "dur", "begin", "repeatCount", "calcMode") if node.get(key) is not None})
        risks["script_elements"] += lower == "script"
        risks["foreign_object_elements"] += lower == "foreignobject"
        risks["style_elements"] += lower == "style"
        for key, value in node.attrib.items():
            attr = local_name(key).lower()
            risks["event_attributes"] += attr.startswith("on")
            if attr in {"href", "src"}:
                resources.append({"element": tag, "attribute": attr, **summarize_resource(value)})
            for target in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", value, re.I):
                resources.append({"element": tag, "attribute": attr, **summarize_resource(target)})
        if lower == "style" and node.text:
            # CSS presence is reported; this inspector does not execute or evaluate it.
            for target in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", node.text, re.I):
                resources.append({"element": tag, "attribute": "text", **summarize_resource(target)})
    def description(kind):
        item = next((node for node in root.iter() if local_name(node.tag).lower() == kind), None)
        return " ".join("".join(item.itertext()).split()) if item is not None else ""
    report = {
        "width": root.get("width"), "height": root.get("height"),
        "viewBox": root.get("viewBox", root.get("viewbox")),
        "title": description("title"), "description": description("desc"),
        "animated": sum(counts.values()) > 0, "animation_counts": counts,
        "durations": sorted({track["dur"] for track in tracks if "dur" in track}),
        "tracks": tracks, "resources": resources,
        "external_resource_count": sum(item["kind"] in {"external", "relative-file"} for item in resources),
        "review_flags": risks,
    }
    return report, root


def read_bounded(handle, limit):
    value = handle.read(limit + 1)
    if len(value) > limit:
        raise ValueError(f"Input exceeds configured byte limit ({limit})")
    return value


def safe_member(info):
    name = info.filename
    parts = PurePosixPath(name).parts
    if name.startswith("/") or ".." in parts or "\\" in name or (parts and ":" in parts[0]):
        raise ValueError("ZIP contains an unsafe member path")
    if stat.S_ISLNK(info.external_attr >> 16):
        raise ValueError("ZIP symlinks are not accepted")
    return not (info.is_dir() or "__MACOSX" in parts or any(part.startswith("._") for part in parts))


def inputs(source: Path, limit):
    if source.suffix.lower() != ".zip":
        if source.suffix.lower() not in {".svg", ".html", ".htm"}:
            raise ValueError("Expected .svg, .html, .htm, or .zip")
        with source.open("rb") as handle:
            yield source.name, read_bounded(handle, limit)
        return
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        if len(infos) > 2000:
            raise ValueError("ZIP contains more than 2000 members")
        budget = limit
        for info in infos:
            if not safe_member(info) or PurePosixPath(info.filename).suffix.lower() not in {".svg", ".html", ".htm"}:
                continue
            if info.file_size > budget:
                raise ValueError("ZIP SVG/HTML members exceed configured expanded byte limit")
            with archive.open(info) as handle:
                value = read_bounded(handle, budget)
            budget -= len(value)
            # Some macOS ZIP names use UTF-8 bytes without setting the ZIP UTF-8 flag.
            name = info.filename
            if not (info.flag_bits & 0x800):
                try:
                    name = name.encode("cp437").decode("utf-8")
                except (UnicodeError, LookupError):
                    pass
            yield name, value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--extract-dir", type=Path, help="Save animated SVG source for inspection; never downloads its resources")
    parser.add_argument("--max-mib", type=float, default=32, help="Maximum total expanded SVG/HTML bytes (default: 32 MiB)")
    args = parser.parse_args()
    if not 0 < args.max_mib <= 512:
        parser.error("--max-mib must be greater than 0 and at most 512")
    try:
        if args.extract_dir:
            if args.extract_dir.is_symlink() or (args.extract_dir.exists() and any(args.extract_dir.iterdir())):
                raise ValueError("Extraction directory must be absent or empty, and not a symlink")
        documents = []
        animations = []
        for name, data in inputs(args.source, int(args.max_mib * 1024 * 1024)):
            source = data.decode("utf-8-sig", errors="replace")
            if name.lower().endswith(".svg"):
                candidates = [source]
                scope, media = "svg-file", []
            else:
                page = PageInspector(source)
                page.feed(source)
                candidates = [raw for raw, inside in page.svgs if inside or not page.has_article]
                scope = "js_content" if page.has_article else "document"
                media = [{key: val for key, val in item.items() if key != "in_article"} for item in page.media if item["in_article"] or not page.has_article]
            document = {"source": name, "scope": scope, "svg_count": len(candidates), "static_svg_count": 0, "animations": [], "media_hints": media, "parse_errors": []}
            for index, raw in enumerate(candidates, 1):
                try:
                    report, root = inspect_svg(raw)
                except (ValueError, ET.ParseError) as error:
                    document["parse_errors"].append({"svg_index": index, "error": str(error)})
                    continue
                if not report["animated"]:
                    document["static_svg_count"] += 1
                    continue
                report["svg_index"] = index
                document["animations"].append(report)
                animations.append((report, root))
            documents.append(document)
        if args.extract_dir:
            args.extract_dir.mkdir(parents=True, exist_ok=True)
            for index, (report, root) in enumerate(animations, 1):
                # Source may contain external/active content. Keep that explicit in JSON;
                # make_preview.py rejects it, and no extracted file is executed here.
                target = args.extract_dir / f"animation_{index:03d}.svg"
                ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
                report["extracted_file"] = str(target)
                report["extraction_note"] = "Source only; review flags and replace external resources before opening or previewing."
        print(json.dumps({"source": str(args.source), "animation_count": len(animations), "documents": documents}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        parser.exit(1, f"inspection failed: {error}\n")


if __name__ == "__main__":
    main()
