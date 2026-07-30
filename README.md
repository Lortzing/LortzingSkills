# LortzingSkills

可复用的 Codex skills。

## Skills 一览

| Skill | 支持平台 | 导出格式 | 说明 |
| --- | --- | --- | --- |
| `video-course-notes` | Bilibili、YouTube | Markdown、HTML、PDF | 将讲座、教程或技术分享整理为结构化、图文并茂的中文课程笔记。 |

## video-course-notes

`video-course-notes` 可根据视频 URL 自动识别 Bilibili 或 YouTube，并生成一种或多种输出：

- `markdown`：适合 Obsidian、GitHub 和后续编辑；
- `html`：适合浏览器阅读和分享；
- `pdf`：适合打印与归档。

它优先使用原始字幕和章节，同时结合视频关键帧、图表、公式、代码和讲者的结论；Bilibili 在字幕不可用时可回退到 Whisper 转写或视觉分析。

### 安装

```bash
cp -R skills/video-course-notes ~/.codex/skills/
```

然后在 Codex 中使用：

```text
$video-course-notes https://www.bilibili.com/video/BV... 导出 markdown 和 pdf
```

或：

```text
$video-course-notes https://www.youtube.com/watch?v=... 导出 html
```

## 来源与修改说明

当前 `video-course-notes` skill 由 [wdkns/wdkns-skills](https://github.com/wdkns/wdkns-skills) 项目导出并修改得到：它将该项目中的 `bilibili-render-pdf` 和 `youtube-render-pdf` 两个 skill 合并为统一入口，并把仅 LaTeX/PDF 的交付方式扩展为 Markdown、HTML、PDF 可选输出。

上游项目源自 `Stefan0219/llm-course-wiki`，并以 GNU GPL v3 发布；本仓库中的派生内容同样采用 GPL-3.0-or-later，详见 [上游许可证](https://github.com/wdkns/wdkns-skills/blob/main/LICENSE)。
