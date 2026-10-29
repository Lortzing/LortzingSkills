# 导出、字体与检查

## 依赖与运行目录

使用任务已有的 Python 环境。检查依赖后再安装，不修改无关项目的环境。

```bash
python -c "import lxml"
ffmpeg -version
```

检查与 HTML 预览使用 Python 标准库。离线渲染需要 Python `lxml`，以及系统 `librsvg`、`Cairo`；`--font` 需要 `fontconfig`。使用 `ctypes.util.find_library` 寻找本机动态库，不能把某台机器的绝对库路径写进作品。

常见安装方式，按用户环境与现有权限选择：

```bash
# macOS / Homebrew
brew install librsvg cairo fontconfig ffmpeg
python -m pip install lxml

# Debian / Ubuntu（系统包安装需要适当权限）
sudo apt-get install librsvg2-2 libcairo2 libfontconfig1 ffmpeg
python -m pip install lxml
```

如果原生依赖不可用，先交付可编辑 SVG 和离线 HTML，明确 GIF / MP4 导出尚未完成。不要把静态帧改扩展名当作动画。

## 字体与自包含文件

优先使用系统已安装的中文字体，或用户授权的本地字体；通过可重复的 `--font /absolute/path/font.otf` 参数给离线渲染器注册字体。

`--font` 只影响本次离线渲染，**不会把字体嵌入 SVG 或 HTML**。向他人分发时，编辑版可能使用接收方的字体回退；要求跨设备固定字形时，应额外交付文字转路径版本，或采用目标环境支持且授权允许的字体嵌入方法。

保留可编辑文字版本。转换完成后检查字形、定位、动画轨道数和关键帧；复杂 `tspan`、双向文字、连字或字距不能用简单的逐字拼接冒充完整排版。

不要把字体二进制文件或第三方网页背景顺手加入代码仓库。确需分发时保留许可证与署名。

## 渲染器范围

本 skill 的离线采样器有意只覆盖可预测的 UI 演示轨道：

| 项目 | 支持方式 |
| --- | --- |
| 属性动画 | 数值 `opacity` |
| 变换动画 | `translate`、`scale`、`rotate` |
| 取值 | `values` 或成对 `from` / `to` |
| 插值 | `linear`、`discrete`、`spline` |
| 时钟 | 固定数值起始时间，秒或毫秒 |
| 重复 | 单次或 `indefinite`，具体边界以脚本的检查结果为准 |
| 输出 | 指定时刻 PNG，或连续 PNG 帧 |

它不等价于浏览器的完整 SVG/SMIL 实现。CSS 动画、事件触发、路径运动、`additive="sum"` 或累积动画会被拒绝。使用 `fill`、`opacity` 等 presentation attributes，不使用 `style` 属性或 `<style>`；复杂样式应先展开为属性。遇到不支持的轨道时，应根据错误调整稿件或切换到有授权的完整渲染环境。

外链、脚本、事件处理器、`foreignObject` 和 DTD/实体声明会被拒绝。对参考文件的分析与对自包含作品的渲染使用不同入口；先把需要的画面重绘或按授权方式内联，再导出。

## 输出示例

下面命令在 skill 根目录执行。`work/` 和 `output/` 是任务目录，不应随 skill 一起提交。

```bash
python scripts/inspect_animation.py work/demo.svg
python scripts/make_preview.py work/demo.svg --output output/demo.html --duration 12
python scripts/render_smil.py work/demo.svg work/frame-5s.png --time 5 --font /path/to/font.otf
python scripts/render_smil.py work/demo.svg work/frames --duration 12 --fps 30 --font /path/to/font.otf
python scripts/export_animation.py work/demo.svg output/demo --duration 12 --formats gif,mp4 --fps 30 --gif-fps 20 --font /path/to/font.otf
```

导出脚本使用 FFmpeg 编码 MP4，并使用全局调色板生成循环 GIF。PNG 帧默认是中间结果；使用 `--keep-frames` 才保留。已有输出需要明确的 `--overwrite`，不要删除整个用户目录来重试。

优先交付：

- **SVG**：可编辑的矢量动画源。
- **HTML**：本地浏览器预览，支持暂停和拖动时间。
- **GIF**：聊天与通用动图展示。
- **MP4**：视频播放与后续剪辑。

普通图片上传流程可能转换或剥离 SVG 动画。用于公众号或其他编辑器时，实际测试其导入方式及最终客户端，不保证任意平台都保留 SMIL。

## 必须实际检查的内容

1. 查看代表帧，覆盖动画前、中、后以及每次状态变化；检查光标确实落到目标按钮。
2. 查看实际 GIF 中的颜色与文字，避免调色板引入明显噪点或缺色。
3. 检查 MP4 编码尺寸、时长、帧率和可播放性。
4. 查看循环交界，避免成功状态闪回、光标跳跃或空白停顿。
5. 在手机显示宽度下检查主要文字；只有在完整浏览器中实际播放过，才宣称浏览器播放已验证。

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,nb_frames,duration \
  -of json output/demo/demo.mp4
```

脚本生成了文件不等于视觉合格。只重复检查具体剩余风险；达到交付要求后停止无关测试。
