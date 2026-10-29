# 动画图层与时间轴模式

## 目录

- [画布与图层](#画布与图层)
- [透明度切换](#透明度切换)
- [光标与缓动](#光标与缓动)
- [点击波纹](#点击波纹)
- [加载与状态同步](#加载与状态同步)
- [文字与视觉规范](#文字与视觉规范)
- [证据与归因](#证据与归因)

## 画布与图层

采用固定逻辑坐标，通过 `viewBox` 缩放显示。让单个 SVG 表达一个完整短流程；每幅图保留一个明确主任务。

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="750" height="720" viewBox="0 0 750 720"
     role="img" aria-labelledby="title description">
  <title id="title">连接工作空间</title>
  <desc id="description">打开设置，选择组织，确认连接的循环操作演示。</desc>
  <rect width="750" height="720" fill="#f6f2e9"/>
  <g id="app-window"><!-- 基础界面 --></g>
  <g id="dialog"><!-- 弹窗 --></g>
  <g id="click-ripples"><!-- 点击反馈 --></g>
  <g id="cursor"><!-- 最上层光标 --></g>
</svg>
```

给同一视觉元素的固定位置和动态变换使用不同层：

```xml
<g transform="translate(120 240)">
  <g>
    <animateTransform attributeName="transform" type="translate"
      values="0 16;0 16;0 0;0 0;0 16"
      keyTimes="0;0.2;0.24;0.9;1" dur="10s" repeatCount="indefinite"/>
    <rect width="510" height="280" rx="18" fill="white"/>
  </g>
</g>
```

## 透明度切换

这条轨道在 2–2.4 秒淡入，保持到 9 秒，随后淡出。标签放在被动画控制的元素内部。

```xml
<g opacity="0">
  <animate attributeName="opacity"
    values="0;0;1;1;0" keyTimes="0;0.2;0.24;0.9;1"
    dur="10s" repeatCount="indefinite"/>
  <!-- 弹窗内容 -->
</g>
```

设置合理的静态初始属性，即使预览工具不播放 SMIL，也能理解图层意图。真正静态封面应单独从合适时刻渲染。

## 光标与缓动

先画一个以尖端为 `(0,0)` 的光标，再移动整个组，让坐标直接对应点击位置。

```xml
<g>
  <animateTransform attributeName="transform" type="translate"
    values="620 530;620 530;140 430;140 430;620 530"
    keyTimes="0;0.08;0.18;0.92;1" dur="10s"
    calcMode="spline"
    keySplines="0 0 1 1;0.4 0 0.2 1;0 0 1 1;0.4 0 0.2 1"
    repeatCount="indefinite"/>
  <path d="M0 0 L0 25 L7 18 L12 30 L17 28 L12 16 L23 16 Z"
    fill="#fff" stroke="#263326" stroke-width="1.5" stroke-linejoin="round"/>
</g>
```

`keySplines` 每段四个数，对应三次贝塞尔的两个控制点；段数等于 `values` 数量减一。给移动段缓动，给保持段线性即可。

## 点击波纹

把圆放在点击点附近的独立定位组中，内层先放大再淡出。下面在 2 秒附近触发一次，之后隐藏到下一周期。

```xml
<g transform="translate(140 430)">
  <g opacity="0">
    <animate attributeName="opacity" values="0;0;0.5;0;0"
      keyTimes="0;0.195;0.2;0.25;1" dur="10s" repeatCount="indefinite"/>
    <animateTransform attributeName="transform" type="scale"
      values="0.2;0.2;1.4;1.4" keyTimes="0;0.2;0.25;1"
      dur="10s" repeatCount="indefinite"/>
    <circle r="18" fill="none" stroke="#377d65" stroke-width="2"/>
  </g>
</g>
```

## 加载与状态同步

- 用父组的透明度控制加载状态的可见时间窗。
- 用子组的短周期旋转，或几个点的离散透明度，表示加载。
- 加载开始时禁用确认按钮的视觉状态；加载结束后切换到成功层。
- 所有结果必须由同一主时间轴决定。不要让独立子循环意外改变主流程。
- 用 `calcMode="discrete"` 切换单选框、文字标签或步骤高亮，避免半选中状态。

## 文字与视觉规范

- 保留文案的可编辑源 SVG；检查中英文标点、数字间距和英文换行。
- 用真实中文字体测试，不依靠系统意外回退。必要时用两行文字，避免无依据缩小字号。
- 重要文字在 750 宽画布上通常需要 20–24 px 或更大；缩到手机显示宽度后再检查。
- 采用少量颜色表示层级：底色、主文字、次文字、边框、强调色、成功色。
- 给成功状态留出足够阅读时间；不要把全部动画时长用于移动光标。
- 文字转路径时另存文件。不要因一次轮廓转换丢失 `animate`、分组或可访问名称。

## 证据与归因

依据实际源码识别最终技术：`animate`、`animateTransform`、`keyTimes`、`dur` 和循环设置。不要仅凭风格将作品归因给某个 AI 或编辑器。背景图片、字体、图标仍各有独立来源和使用条件。

参考规范：

- [MDN：SVG animation with SMIL](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_animation_with_SMIL)
- [MDN：animateTransform](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/animateTransform)
