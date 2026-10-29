#!/usr/bin/env python3
"""Create a single-file offline playback page for a self-contained declarative SVG."""
from __future__ import annotations

import argparse
import base64
import html
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ALLOWED = set("svg g defs desc title rect circle ellipse line polyline polygon path text tspan textPath symbol use clipPath mask linearGradient radialGradient stop pattern marker filter feGaussianBlur feOffset feBlend feColorMatrix feComponentTransfer feFuncR feFuncG feFuncB feFuncA feComposite feFlood feMerge feMergeNode feDropShadow feMorphology feTurbulence feDisplacementMap image animate animateTransform animateMotion mpath".split())


def clean_svg(path: Path):
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("SVG exceeds 32 MiB")
    raw = path.read_bytes()
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise ValueError("DOCTYPE and ENTITY declarations are not allowed")
    root = ET.fromstring(raw)
    if root.tag not in {"svg", "{" + SVG_NS + "}svg"}:
        raise ValueError("Expected an SVG root element")
    for node in root.iter():
        if node.tag.startswith("{"):
            namespace, tag = node.tag[1:].split("}", 1)
            if namespace != SVG_NS:
                raise ValueError("Only SVG-namespace elements are allowed")
        else:
            tag = node.tag
        if tag not in ALLOWED:
            raise ValueError(f"Unsupported element <{tag}>; use declarative SVG shapes and SMIL")
        for key, value in node.attrib.items():
            attr = key.rsplit("}", 1)[-1].lower()
            if attr.startswith("on") or attr in {"style", "base"}:
                raise ValueError(f"Attribute {key!r} is not allowed; use SVG presentation attributes")
            if attr in {"href", "src"} and value and not value.startswith("#"):
                if tag != "image" or not re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+", value):
                    raise ValueError("External references and active data URLs are not allowed")
                base64.b64decode(re.sub(r"\s", "", value.split(",", 1)[1]), validate=True)
            if "\\" in value:
                raise ValueError("Escaped attribute values are not supported")
            if re.search(r"url\s*\(", value, re.I):
                targets = re.findall(r"url\s*\(([^)]*)\)", value, re.I)
                if len(targets) != len(re.findall(r"url\s*\(", value, re.I)):
                    raise ValueError("Malformed url() attribute value")
                for target in targets:
                    if not re.fullmatch(r"\s*['\"]?#[A-Za-z_][\w:.-]*['\"]?\s*", target):
                        raise ValueError("Only local fragment url(#id) references are allowed")
            if tag in {"animate", "animateTransform", "animateMotion"} and attr == "attributename":
                target = value.lower().split(":")[-1]
                if target.startswith("on") or target in {"href", "src", "style", "base", "id", "class"}:
                    raise ValueError("Animation may not change executable or resource-bearing attributes")
    if root.tag == "svg":
        root.set("xmlns", SVG_NS)
    return ET.tostring(root, encoding="unicode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, required=True, help="Main loop duration in seconds")
    parser.add_argument("--title", default="SVG 动画预览")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be finite and greater than zero")
    try:
        if args.output.resolve() == args.svg.resolve():
            raise ValueError("Output must differ from source SVG")
        if args.output.is_symlink() or (args.output.exists() and not args.overwrite):
            raise ValueError("Output exists; choose another path or pass --overwrite")
        svg = clean_svg(args.svg)
        title = html.escape(args.title, quote=True)
        template = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>__TITLE__</title><style>
*{box-sizing:border-box}body{margin:0;padding:24px 14px;background:#e9e6de;color:#2a2d26;font-family:system-ui,-apple-system,"PingFang SC",sans-serif}
main{max-width:850px;margin:auto}.frame{overflow:hidden;border-radius:12px;background:#fff;box-shadow:0 12px 35px #30281712}.frame>svg{display:block;max-width:100%;width:100%;height:auto}
.controls{display:flex;align-items:center;gap:10px;padding:18px 0}button{padding:9px 15px;border:1px solid #c9c4b8;border-radius:30px;background:#faf8f3;color:inherit;font:inherit;white-space:nowrap;cursor:pointer}input{flex:1;min-width:40px;accent-color:#35735a}output{min-width:90px;text-align:right;font-variant-numeric:tabular-nums;font-size:13px;color:#696d61}.note{margin:0;text-align:center;font-size:12px;color:#777b70}button:focus-visible,input:focus-visible{outline:3px solid #47967a;outline-offset:3px}
@media(max-width:480px){body{padding:10px 7px}.controls{gap:7px}button{padding:8px 10px;font-size:13px}output{min-width:75px;font-size:11px}}
</style></head><body><main><div class="frame">__SVG__</div>
<div class="controls"><button type="button" data-control="play" aria-pressed="false">暂停</button><button type="button" data-control="restart">重播</button><input data-control="range" type="range" aria-label="播放进度" min="0" max="__DURATION__" step="0.01" value="0"><output data-control="time"></output></div>
<p class="note">离线 SVG 预览 · 可暂停、重播和拖动进度</p></main><script>
const frame=document.querySelector('main > .frame'),svg=frame.querySelector(':scope > svg'),controls=document.querySelector('main > .controls'),play=controls.querySelector('[data-control="play"]'),restart=controls.querySelector('[data-control="restart"]'),range=controls.querySelector('[data-control="range"]'),time=controls.querySelector('[data-control="time"]'),duration=__DURATION__;
function sync(){const paused=svg.animationsPaused();play.textContent=paused?'播放':'暂停';play.setAttribute('aria-pressed',String(paused));}
play.addEventListener('click',()=>{svg.animationsPaused()?svg.unpauseAnimations():svg.pauseAnimations();sync();});
restart.addEventListener('click',()=>{svg.setCurrentTime(0);svg.unpauseAnimations();sync();});
range.addEventListener('input',()=>{svg.pauseAnimations();svg.setCurrentTime(Number(range.value));sync();});
if(matchMedia('(prefers-reduced-motion: reduce)').matches){svg.pauseAnimations();sync();}
function tick(){const t=svg.getCurrentTime()%duration;range.value=t;time.textContent=t.toFixed(1)+' / '+duration+' s';requestAnimationFrame(tick);}requestAnimationFrame(tick);
</script></body></html>'''
        # Insert SVG last: its text cannot affect the trusted placeholders.
        output = template.replace("__TITLE__", title).replace("__DURATION__", repr(args.duration)).replace("__SVG__", svg)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(args.output)
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, f"preview failed: {error}\n")


if __name__ == "__main__":
    main()
