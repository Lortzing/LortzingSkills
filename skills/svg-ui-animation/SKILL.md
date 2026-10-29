---
name: svg-ui-animation
description: Create, inspect, and export editable SVG + SMIL interface animations, product walkthroughs, and short instructional motion graphics. Use when the user asks how a UI animation was made, requests a similar animated illustration, provides an SVG/HTML/offline webpage ZIP as a reference, or asks for SVG 动图、公众号操作演示、鼠标点击动画、弹窗动画、GIF or MP4 exports. Produce a working animation and editable source when creation is requested.
---

# SVG 界面动画

把文字、界面和动作拆成矢量图层与时间轴，交付可播放的小样和可修改的源文件。优先用 SVG + SMIL 表达精确的文字、按钮、光标和流程状态。

## 1. 确定内容与输出

- 从当前对话复用主题、参考风格、发布场景和既有文件。信息足够时直接制作。
- 未指定规格时，采用 `750 × 720` 画布、`10–12 秒` 循环、三至五个主要状态；按内容调整比例和时长。
- 默认保留可编辑 SVG，并生成离线 HTML 预览；需要直观演示或用户要求时，再交付 GIF / MP4。
- 区分自动演示与可点击产品原型。光标与点击反馈可由图形模拟；不要暗示动画已经操作了真实服务。
- 对真人、复杂三维、连续自然运动等内容，先选择适合该内容的制作方式，不强行套用本模板。

## 2. 检查参考素材

先实际查看图片、动画帧或源码，再判断实现方式。读取离线网页时只解析内容，不执行其脚本。

```bash
python scripts/inspect_animation.py /absolute/path/reference.zip
python scripts/inspect_animation.py /absolute/path/reference.html --extract-dir work/reference-svg
```

检查 SVG / GIF / 视频 / CSS 动画的线索、画布、循环时长、图层、字体、外部图片与编辑器标记。只在源码有证据时断言具体技术；没有生成器标记时，不猜测作者用了哪款软件或 AI。

链接无法读取时，使用用户提供的动图、录屏、截图或离线归档。不要把未看到的参考描述为已复刻。提取后的 SVG 仍是原始参考材料，可能有外链；先读检查结果，再决定重绘或替换资源。

## 3. 先排分镜，再写 SVG

用一张简短时间表约定每个状态、光标位置、点击时刻和阅读停顿。例如：

| 时间 | 状态 | 动作 |
| --- | --- | --- |
| 0–2 秒 | 工作台 | 光标移向设置，点击一次 |
| 2–5 秒 | 组织选择 | 弹窗出现，选中一项 |
| 5–8 秒 | 提交 | 点击确认，短暂加载 |
| 8–11 秒 | 成功 | 展示结果，保留阅读时间 |
| 11–12 秒 | 收尾 | 淡出并在不可见时复位 |

保持同一主周期。用 `keyTimes × dur` 换算实际时刻；让循环末尾和开头的可见状态一致。重置光标时先隐藏，避免可见跳跃。

## 4. 绘制界面并添加动画

从 [assets/ui-demo.svg](assets/ui-demo.svg) 复制到任务输出目录，改文案、图层和时间轴。按任务内容重新设计，避免只改标题。

- 设置 `xmlns`、`viewBox`、数值 `width/height`、可读的 `title/desc`。
- 使用 `rect / circle / line / path / text / g` 构建界面；为场景、按钮和光标设置可读 ID。
- 用稳定网格对齐，统一圆角、边距与描边；确保关键文字在手机宽度下仍可读。
- 为中文选择真实可用的中文字体。保留普通 `text` 的编辑版；需要跨设备固定字形时，另存文字转路径版并检查动画仍然存在。
- 用 `<animate attributeName="opacity">` 切换状态，用 `<animateTransform>` 控制位移、缩放和旋转。
- 为随附工具使用 SVG presentation attributes（如 `fill`、`opacity`）；不要混入 `style` 属性、样式表或 CSS 动画。
- 用嵌套 `g` 分别承担定位、平移和缩放；避免一条变换轨道覆盖原有布局。
- 点击波纹采用圆形放大与透明度衰减；先移动光标，再触发波纹和界面变化。
- 弹窗淡入可搭配小幅上移；让加载状态只在对应时间窗可见。
- 优先制作无脚本、无外链的自包含 SVG。保留第三方素材的授权与署名要求。

需要直接复用的轨道写法、分组方式和缓动参数时，读取 [references/animation-patterns.md](references/animation-patterns.md)。

## 5. 预览与导出

所有命令中的相对脚本路径均相对于本 skill 根目录；输出写入任务工作目录。

```bash
# 本地可播放预览，支持暂停、重播和拖动进度
python scripts/make_preview.py work/demo.svg --output output/demo.html --duration 12

# 在指定时刻取样；中文示例传入可用字体的绝对路径
python scripts/render_smil.py work/demo.svg work/frame.png --time 5 --font /absolute/path/chinese-font.otf

# 输出 GIF 与 MP4
python scripts/export_animation.py work/demo.svg output/demo --duration 12 --fps 30 --gif-fps 20 --formats gif,mp4 --font /absolute/path/chinese-font.otf
```

依赖：检查与预览脚本使用 Python 标准库；渲染脚本另外需要 `lxml`、系统 `librsvg / Cairo`，添加本地字体时需要 `fontconfig`；视频导出还需要 `ffmpeg`。先检查环境，再按需要安装；不要自动下载字体或假设中文字体已存在。

**离线采样器只支持本 skill 使用的 SMIL 子集。** 它用于数值透明度及 `translate / scale / rotate`，支持固定起始时间、`values` 或 `from/to`、`linear / discrete / spline`。遇到复杂路径运动、事件触发、CSS 动画等未支持机制，保留原稿并明确说明，改用可用的完整渲染器或重写轨道；不能把错误快照当成成功导出。

需要依赖安装、字体处理、格式选择或导出排查时，读取 [references/export-and-qa.md](references/export-and-qa.md)。

## 6. 检查并交付

1. 解析 XML，检查 ID、轨道值与 `keyTimes` 数量、单调性、缓动段数及主周期。
2. 渲染开场、点击、弹窗、选中、加载、成功、循环衔接等代表帧，实际查看字号、对齐、遮挡、缺字和光标落点。
3. 确认 GIF / MP4 的尺寸、时长、帧率、循环设置与源 SVG 相符；检查实际编码后的画面。
4. 保留编辑版 SVG。可选交付文字转路径版、HTML 预览、GIF、MP4；根据用户用途选择，不堆积重复文件。
5. 用所在环境允许的持久化方式保存交付物；仓库任务遵循该仓库的提交规范。不要只返回临时工作区路径。
6. 展示动画或代表帧，给出文件入口，并说明主题、时长、可修改内容以及实际存在的限制。

用实际结果报告完成情况。只做了静态截图时，不宣称已验证完整动画播放；仅保存到 GitHub 时，不宣称已安装到用户的技能环境。
