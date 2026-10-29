# LortzingSkills

可复用的 Codex skills。

## Skills 一览

| Skill | 输入 / 场景 | 导出格式 | 说明 |
| --- | --- | --- | --- |
| `video-course-notes` | Bilibili、YouTube | Markdown、HTML、PDF | 将讲座、教程或技术分享整理为结构化、图文并茂的中文课程笔记。 |
| `svg-ui-animation` | 文字描述、SVG、HTML、离线网页归档 | SVG、HTML、GIF、MP4 | 制作可编辑的界面操作动画，支持光标、点击波纹、弹窗、加载与成功状态。 |

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

## svg-ui-animation

[`svg-ui-animation`](skills/svg-ui-animation/SKILL.md) 将界面操作过程整理为 SVG + SMIL 时间轴动画，包含参考素材分析、分镜、矢量绘制、离线预览、逐帧渲染与 GIF / MP4 导出。

附带一份可修改的中文界面示例，以及分析、预览、渲染、导出四个脚本。SVG 和 HTML 可独立查看；视频导出需要 Python `lxml`、系统 `librsvg` / `Cairo` / `fontconfig` 和 FFmpeg，详见 skill 中的导出说明。

### 安装与使用

```bash
cp -R skills/svg-ui-animation ~/.codex/skills/
```

```text
$svg-ui-animation 制作“打开设置 → 选择组织 → 连接成功”的 12 秒循环动画，使用米白背景，导出可编辑 SVG、GIF 和 MP4。
```

也可以提供参考文件：

```text
$svg-ui-animation 分析这个网页归档里的动图，用相同技术为我的产品制作操作教程。
```

## 来源与修改说明

当前 `video-course-notes` skill 由 [wdkns/wdkns-skills](https://github.com/wdkns/wdkns-skills) 项目导出并修改得到：它将该项目中的 `bilibili-render-pdf` 和 `youtube-render-pdf` 两个 skill 合并为统一入口，并把仅 LaTeX/PDF 的交付方式扩展为 Markdown、HTML、PDF 可选输出。

上游项目源自 `Stefan0219/llm-course-wiki`，并以 GNU GPL v3 发布；本仓库中的派生内容同样采用 GPL-3.0-or-later，详见 [上游许可证](https://github.com/wdkns/wdkns-skills/blob/main/LICENSE)。

`svg-ui-animation` 为本仓库新增的工作流、脚本与原创示例，遵循本仓库许可证。其技术参考见 skill 的 `references/`；第三方字体、图片与网页内容不随该 skill 分发。
