---
name: 海大互助 · Campus Exchange
description: 水彩校园入口与湖绿、暖白的校园互助工作界面。
colors:
  primary: "#226356"
  primary-deep: "#174f44"
  ink: "#183d3c"
  muted: "#60736e"
  canvas: "#f6f7f2"
  surface: "#fffef9"
  border: "#dce5dd"
  warm: "#fff9e9"
typography:
  display:
    fontFamily: "Inter, 'Segoe UI', sans-serif"
    fontSize: "clamp(64px, 10.9vw, 170px)"
    fontWeight: 750
    lineHeight: 1
    letterSpacing: ".105em"
  headline:
    fontSize: "clamp(28px, 3vw, 38px)"
    lineHeight: 1.25
  title:
    fontSize: "15px"
  body:
    fontFamily: "'Aptos', 'Segoe UI', 'Noto Sans SC', 'Microsoft YaHei', sans-serif"
  label:
    fontSize: "12px"
    fontWeight: 700
rounded:
  field: "9px"
  panel: "12px"
  card: "14px"
  dialog: "18px"
  pill: "999px"
spacing:
  compact: "8px"
  control: "14px"
  section: "16px"
  generous: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#fff"
    rounded: "{rounded.pill}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.primary-deep}"
  button-outline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 14px"
  button-home-primary:
    backgroundColor: "{colors.warm}"
    textColor: "#193f35"
    rounded: "{rounded.pill}"
    padding: "14px 27px"
  input:
    backgroundColor: "#f5f7ef"
    rounded: "{rounded.field}"
    padding: "9px 10px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
---

# Design System: 海大互助 · Campus Exchange

## Overview

**Creative North Star: "湖畔的分享入口"**

首页以用户提供的水彩校园为视觉锚点：湖面、亭台、树木与塔楼共用一个坐标系，奶油白 EXCHANGE 大字保持醒目。进入功能页后，画面的湖绿与暖纸色转化为清晰、紧凑的操作界面。

工作界面以内容、状态和操作为中心；圆润控件、细边框和克制的阴影延续首页的温度。沿用现有字体栈与本地图片，不引入新的字体或组件库。

**Key Characteristics:**
- 原图水彩校园与大幅奶油白标题。
- 湖绿主操作、暖白表面、低对比细边框。
- 胶囊导航、紧凑列表、短促切换与减少动态支持。

## Colors

配色以湖绿为主轴，以暖纸色承接内容；具体色值由前置 token 定义。

### Primary
- **湖绿**（primary）：主要按钮、选中线条和关键链接。
- **深湖绿**（primary-deep）：主按钮悬停及强调状态文字。

### Neutral
- **墨绿**（ink）：工作页面标题与主要文字。
- **灰绿**（muted）：描述、辅助信息与次要操作。
- **浅纸底**（canvas）：功能页背景。
- **暖白**（surface）：导航、列表及面板底色。
- **纸边灰绿**（border）：面板、表单和分隔线。
- **奶油白**（warm）：水彩首页主按钮及次按钮文字；画面标题保留原有近似暖白。

**The Theme Authority Rule.** `frontend/src/exchange-theme.css` 是本次视觉适配的最终覆盖层，必须在继承的 `style.css` 后加载。历史 `--coral`、`--coral-dark` 别名现已映射到湖绿体系，不代表珊瑚色品牌。

## Typography

**Display Font:** Inter、Segoe UI、sans-serif，沿用首页现有栈。
**Body Font:** Aptos、Segoe UI、Noto Sans SC、Microsoft YaHei、sans-serif，沿用工作界面现有栈。

**Character:** 英文大字承担首页识别，中文工作内容使用清晰的无衬线文字。字体名称是现有回退栈，项目未新增字体下载。

- **Display:** 使用前置 display token；移动端缩为 `clamp(44px, 11.7vw, 94px)`，字距收为 `.035em`。
- **Headline:** 功能页主标题使用 headline token。
- **Title:** 列表标题使用 title token，描述通常为 12px，页面说明为 13px。
- **Body:** 首页说明使用 14px、1.95 行高；移动端为 12px、1.9 行高，中文段落最大宽度为 28em。
- **Label:** 主要操作使用 label token；800px 以下弹窗表单文字保持 16px。

## Layout

功能页居中，最大宽度为 1380px，横向留白随视口伸缩；列表以紧凑的图片、内容和操作列排列。桌面广场的两列内容在继承样式的 1120px 断点下转为单列。

顶栏在功能页吸顶，在首页覆盖于画布上；首页品牌文字有奶油白底以保证辨识。1150px 以下压缩顶栏间距并收起顶部发布按钮；800px 以下切换为可展开的两列导航菜单，筛选区改为双列，搜索与提交各占整行。460px 以下继续压缩条目和表单。页面最小宽度为 320px。

首页的四张校园图片使用相同的 `object-fit: cover` 与 `object-position: 54% center`，避免亭台层错位。移动端保留整幅视觉关系，并分别调整标题和正文位置。滚动条采用细绿灰滑块，分类条可横向滚动。

## Elevation & Depth

工作页主要依靠暖白表面和细边框分层，列表与业务面板不以阴影突出。账户菜单和移动导航使用轻柔环境阴影；弹窗拥有更深阴影与半透明深绿遮罩。首页文字的柔和阴影仅用于水彩上的可读性。

按钮状态通常以 160ms 颜色变化反馈，页面切换使用 120ms 透明度和 160ms 轻微位移；水彩分层仅播放一次 800–1100ms 的进入动画。系统请求减少动态时禁用动画与过渡。

## Shapes

导航、主次按钮和状态标签使用胶囊形；输入框、筛选面板、内容容器和弹窗依次使用前置圆角 token。边框通常为 1px；保持列表行的水平分隔，避免把每条内容再套成漂浮卡片。

## Components

### Buttons

主按钮为湖绿底白字，次按钮为暖白底墨绿字；均保留清晰边界。悬停以颜色变化反馈，工作页按钮与列表行不整体抬升。首页主按钮反转为奶油白底，次按钮为透明深绿底与浅色边框。

键盘焦点使用金色 3px 外轮廓，控件外移 3px；禁用态降低透明度并保留不可用光标。不要用颜色变化替代可见焦点。

### Navigation

桌面为浅底胶囊导航组，激活项为深绿底浅色字。800px 以下使用菜单按钮展开同一组真实入口；账户菜单独立于主导航，使用相同的圆角、暖白表面和悬停底色。

### Chips / Cards

分类筛选为紧凑胶囊，选中后使用浅绿背景与绿边框。内容容器使用暖白底、细边框与 card 圆角；资源与技能可保留各自的轻量辅助色，不将辅助色升级为主品牌色。

### Inputs / Fields

输入框使用浅灰绿底、细边框与 field 圆角，聚焦时边框转绿并保留键盘焦点轮廓。表单保持可伸缩宽度；移动端弹窗表单使用 16px 字号。

### Dialog / Authentication

弹窗使用 dialog 圆角、滚动内容与深绿遮罩。登录选择器固定为三个等宽选项，选中项使用湖绿底白字；关闭操作与标题、选项之间保留独立空间。

### Icons

共享导航与主要操作沿用 `AppIcon.vue` 的内联线性 SVG：默认 19px、1.7 描边、圆端点。具体图标按已有动作选择，不以任意 Unicode 字符扩充图标系统。

## Do's and Don'ts

### Do:
- **Do** 保留首页原有水彩层与 EXCHANGE 字样的识别关系，并用浅底保证品牌文字可读。
- **Do** 让新工作页面沿用湖绿操作、暖白表面、细边框与紧凑信息密度。
- **Do** 同时保留键盘焦点、移动导航和减少动态体验。
- **Do** 以最终主题覆盖层和实际功能组件为设计依据。

### Don't:
- **Don't** 从历史 `--coral` 命名恢复旧珊瑚主色，或让旧样式覆盖最终主题。
- **Don't** 把首页的水彩进入动画扩展为持续滚动视差或工作列表的整体抬升。
- **Don't** 把继承代码中的零散字形图标或旧式装饰标签当作新组件规范。
