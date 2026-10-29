#!/usr/bin/env python3
"""Export the supported SVG/SMIL subset to MP4 and/or GIF with FFmpeg."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from render_smil import AnimationError, ensure_safe_output, frame_count, load_svg, pixel_dimensions, render_frames


def run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise AnimationError(f"FFmpeg failed: {result.stderr.strip()[-3000:]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--formats", default="gif,mp4", help="gif, mp4, or gif,mp4")
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--gif-fps", type=int, help="GIF fps (default: min(20, --fps))")
    parser.add_argument("--gif-width", type=int, help="Optional GIF width; height keeps the canvas ratio")
    parser.add_argument("--font", type=Path, action="append", default=[])
    parser.add_argument("--background", default="#ffffff", help="Opaque background for video export")
    parser.add_argument("--keep-frames", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        formats = list(dict.fromkeys(item.strip() for item in args.formats.split(",")))
        if not formats or any(item not in {"gif", "mp4"} for item in formats):
            raise AnimationError("--formats must contain gif, mp4, or both")
        frame_count(args.duration, args.fps)
        gif_fps = args.gif_fps if args.gif_fps is not None else min(20, args.fps)
        if "gif" in formats and (gif_fps <= 0 or gif_fps > args.fps):
            raise AnimationError("--gif-fps must be positive and no greater than --fps")
        if args.gif_width is not None and args.gif_width <= 0:
            raise AnimationError("--gif-width must be positive")
        executable = shutil.which("ffmpeg")
        if not executable:
            raise AnimationError("FFmpeg is required. Install it and make ffmpeg available on PATH.")
        document = load_svg(args.svg)
        width, height = pixel_dimensions(document, args.scale)
        stem = args.svg.stem
        ensure_safe_output(args.output_dir)
        outputs = {fmt: args.output_dir / f"{stem}.{fmt}" for fmt in formats}
        for path in outputs.values():
            ensure_safe_output(path)
            if path.exists() and (not args.overwrite or not path.is_file()):
                raise AnimationError(f"Output exists: {path}; use --overwrite deliberately")
            if path.resolve() == args.svg.resolve():
                raise AnimationError("Input and output must be different paths")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="svg-ui-animation-", dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            # macOS may expose its system temporary directory through /var.
            # Resolve our own newly created directory before output checks.
            temporary = Path(temporary).resolve()
            frames = args.output_dir / f"{stem}_frames" if args.keep_frames else temporary / "frames"
            metadata = render_frames(document, frames, args.duration, args.fps, args.scale,
                                     args.font, args.background, args.overwrite)
            sequence = str(frames / "frame_%06d.png")
            common = [executable, "-hide_banner", "-loglevel", "error", "-y" if args.overwrite else "-n"]
            source = ["-framerate", str(args.fps), "-i", sequence]
            if "mp4" in outputs:
                run(common + source + ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(outputs["mp4"])])
            if "gif" in outputs:
                gif_width = args.gif_width or width
                gif_height = max(1, round(height * gif_width / width))
                filters = f"fps={gif_fps},scale={gif_width}:{gif_height}:flags=lanczos"
                palette = temporary / "palette.png"
                run(common + source + ["-vf", filters + ",palettegen=max_colors=256:stats_mode=diff",
                    "-frames:v", "1", "-update", "1", str(palette)])
                run(common + source + ["-i", str(palette), "-lavfi",
                    filters + "[sample];[sample][1:v]paletteuse=dither=bayer:bayer_scale=4",
                    "-loop", "0", str(outputs["gif"])])
            print(json.dumps({"render": metadata, "outputs": [
                {"path": str(path.resolve()), "bytes": path.stat().st_size} for path in outputs.values()
            ], "frames_directory": str(frames.resolve()) if args.keep_frames else None}, ensure_ascii=False))
    except (AnimationError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
