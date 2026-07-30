---
name: video-course-notes
description: Turn a Bilibili or YouTube lecture, tutorial, or technical talk into structured, figure-rich Chinese course notes. Use when the user provides a Bilibili or YouTube URL and asks for Markdown, HTML, PDF, or a combination. Prefer the video's actual teaching content, timestamped subtitles, chapters, original cover, and high-value key frames; Bilibili supports CC subtitles, Whisper fallback, and visual-only fallback.
license: GPL-3.0-or-later
metadata:
  derived_from: https://github.com/wdkns/wdkns-skills
---

# Video Course Notes

Create complete, teachable Chinese notes from a Bilibili or YouTube video. This skill merges the platform-specific acquisition practices of `bilibili-render-pdf` and `youtube-render-pdf`, then renders one canonical note into Markdown, HTML, PDF, or multiple requested formats.

## First decide the delivery

1. Detect the platform from the URL: Bilibili (`bilibili.com`, `b23.tv`, BV/av identifiers) or YouTube (`youtube.com`, `youtu.be`).
2. Read the requested format. Accept `markdown`/`md`, `html`, `pdf`, or a comma-separated combination.
3. If no format is specified, deliver Markdown by default. Ask only when format changes the user's intent materially.
4. Create a working directory that keeps metadata, subtitles, video, frame assets, source note, and final outputs together.

Never claim a generated document is based on video content you did not inspect. Preserve timestamps for claims, figures, and quotations.

## Quality bar

The note should read as if a strong human teacher is guiding the reader:

- Explain motivation, the main idea, mechanism, example/evidence, and takeaway in a logical sequence.
- Reorganize the material pedagogically; do not dump subtitles in chronological order.
- Use actual diagrams, formulas, code, UI states, demonstrations, and speaker conclusions when they matter.
- Distinguish speaker claims from your synthesis or inference.
- End with a synthesis: core ideas, common pitfalls, practical next steps, and unresolved questions when applicable.

## Acquire sources

### Shared procedure

1. Inspect metadata first: title, creator, duration, chapters, upload date, description, thumbnail, and subtitle availability.
2. Download the highest usable resolution for figure extraction, not merely the highest advertised format.
3. Download the official cover/thumbnail and use it as the note cover whenever available.
4. Prefer manually authored subtitles over auto-generated subtitles. Preserve timestamps in the source artifact.
5. Keep a source manifest containing URLs, selected tracks, download choices, and limitations.

### YouTube

- Prefer the video's manual CC track and chapter structure.
- Use `yt-dlp` to inspect formats and subtitle tracks before downloading.
- Choose the language closest to the video or to the user's requested language.

### Bilibili

- Detect multipart videos and state the selected P range. Ask the user only if the URL has multiple relevant parts and no reasonable scope is clear.
- Subtitle fallback order: Bilibili CC subtitle → Whisper transcription from downloaded audio → visual-only analysis with explicit caveats.
- Filter platform housekeeping such as likes, coins, follows, and unrelated promotions from teaching notes.
- High-resolution access may require user-authorized browser cookies. Do not extract, reuse, or transmit cookies without explicit permission; otherwise use the best public stream.

## Long videos

For videos longer than 20 minutes or transcripts with more than 300 entries, split analysis by chapters first, then coherent time windows. Maintain a shared outline, terminology table, and timestamp map. Merge only after checking for missing concepts, duplicate explanations, inconsistent notation, and broken transitions.

## Select evidence and figures

1. Build a timestamped outline from chapters and transcript.
2. Inspect candidate frames around every major conceptual transition and any visual explanation.
3. Keep frames only when they add information: diagrams, equations, code, data plots, demonstrations, UI states, or comparisons.
4. Crop only when it makes the teaching point clearer; retain enough context to understand the image.
5. Every selected figure needs a caption explaining why it matters and a timestamp/source note.
6. Avoid decorative, repetitive, blurry, or copyright-irrelevant screenshots.

## Build one canonical note

Use this structure unless the material calls for a clearer one:

1. Title, creator, platform, link, duration, and cover
2. What the video teaches and who it is for
3. Table of contents
4. Prerequisites and notation
5. Main sections and subsections
6. Worked examples, code, formulas, or visual explanations
7. Final synthesis and practical checklist
8. Sources, timestamps, and limitations

Use clear H1/H2/H3 hierarchy. Put figures next to the explanation they support. Keep source timestamps in a compact form such as `[12:34]`.

## Render outputs

### Markdown

- Produce portable CommonMark with relative image paths.
- Include title metadata, table of contents, figure captions, timestamp links/notes, and a limitations section.
- Ensure it is readable without HTML-only features.

### HTML

- Render semantic HTML from the canonical note.
- Use UTF-8, responsive typography, a printable stylesheet, accessible `alt` text, and local relative assets.
- Verify internal anchors, image paths, and Chinese text rendering.

### PDF

- Produce PDF from the canonical Markdown/HTML using a dependable local renderer (for example Pandoc plus a suitable PDF engine, or a browser print pipeline).
- Embed the cover and selected figures; use readable Chinese-capable fonts.
- Inspect the final PDF for page overflow, missing glyphs, broken images, and unusable captions.

When multiple formats are requested, render from the same canonical source and report all created files.

## Validation before delivery

- Confirm the platform, title, URL, duration, requested outputs, and actual outputs.
- Check that claims are grounded in the inspected transcript/video and that figures are not invented.
- Check timestamp consistency and links.
- Check Markdown links/images, HTML structure/assets, and PDF page rendering respectively.
- State known gaps honestly: unavailable subtitles, restricted resolution, uninspected segments, or uncertain terminology.

## Suggested tools

- `yt-dlp` for metadata, subtitles, thumbnails, audio, and video.
- `ffmpeg` for clips, audio normalization, and frame extraction.
- `openai-whisper` for Bilibili audio transcription when CC subtitles are unavailable.
- Pandoc and a PDF engine, or a browser printing pipeline, for PDF output.

Use only videos and assets the user is entitled to access. Respect platform terms, copyright, and privacy.
