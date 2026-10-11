# Bilibili Video Notes 📝

> **B站视频笔记生成工具** — 从B站教育/讲课视频自动生成带截图的DOCX学习笔记，如果觉得有用的话欢迎点一下星标哟🤗
>
> 全流程：下载视频 + 字幕 → 抽帧 → OCR 去重 → 字幕定位候选帧 → 视觉评分与内容提取 → 融合生成 DOCX
>
> 🍴 本仓库是 [asdhabdua/bilibili-video-notes-skill](https://github.com/asdhabdua/bilibili-video-notes-skill) 的 fork。
> 相对上游改了什么，见 **[相对上游的改进](#-相对上游的改进)**。

<p align="center">
  <img src="https://img.shields.io/badge/bilibili-1eabc9.svg?logo=bilibili&logoColor=white&style=flat-square" alt="Bilibili">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg?logo=python&style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License">
</p>

## 目录

- [一键安装（复制粘贴给 AI）](#-%E4%B8%80%E9%94%AE%E5%AE%89%E8%A3%85%E5%A4%8D%E5%88%B6%E7%B2%98%E8%B4%B4%E7%BB%99-ai)
- [功能特点](#-%E5%8A%9F%E8%83%BD%E7%89%B9%E7%82%B9)
- [快速开始](#-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
- [详细使用教程(包括如何让AI代劳配置)](#-%E8%AF%A6%E7%BB%86%E4%BD%BF%E7%94%A8%E6%95%99%E7%A8%8B)
- [配置好之后如何使用](#-%E9%85%8D%E7%BD%AE%E5%A5%BD%E4%B9%8B%E5%90%8E%E5%A6%82%E4%BD%95%E4%BD%BF%E7%94%A8)
- [完整工作流](#-%E5%AE%8C%E6%95%B4%E5%B7%A5%E4%BD%9C%E6%B5%81)
- [命令参考](#-%E5%91%BD%E4%BB%A4%E5%8F%82%E8%80%83)
- [常见问题](#-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)
- [Agent 使用](#-agent-%E4%BD%BF%E7%94%A8)
- [目录结构](#-%E7%9B%AE%E5%BD%95%E7%BB%93%E6%9E%84)
- [相对上游的改进](#-%E7%9B%B8%E5%AF%B9%E4%B8%8A%E6%B8%B8%E7%9A%84%E6%94%B9%E8%BF%9B)
- [License / 反馈](#-license)

---

## ⚡ 一键安装（复制粘贴给 AI）

```
请帮我安装 bilibili-video-notes-skill：

git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
cd bilibili-video-notes-skill
pip install -r scripts/requirements.txt

安装完成后，配置 .env 和 bilibili_cookies.txt，然后读取 README.md 了解如何使用。
```

---

## ✨ 功能特点

- 🎬 **自动下载** B站视频和 AI 字幕（SESSDATA cookie）
- 📸 **scene 抽帧 + 30s 保底**：抓 PPT 翻页，兜底不漏，比全覆盖少约 67% 的帧
- 🔍 **OCR + 感知哈希双重去重**，129帧 → 20-40帧，不丢有价值内容
- 🧠 **默认由 Agent 自身多模态识图**，外部视觉 API 只是可选后备
- 🎯 **字幕定位候选帧 + 视觉评分/提取**，选出每个知识点最完整的一帧
- 📝 **融合字幕+截图内容**生成结构化DOCX笔记
- 🧾 **三档方案**：精读 / 过一遍 / 总结，按"这次拿它做什么"选
- 🧹 **清理走回收站**，不做永久删除
- 🤖 **多 Agent 支持**：Kimi / Claude Code / Codex CLI

## 📊 效果对比

| 输入 | 输出 |
|------|------|
| 21分钟B站视频 | 7-12张精选截图 + 完整知识点DOCX |
| 129帧原始截图 | 20-40帧去重 → 字幕定位候选 → 精选 7-12 帧 |
| AI 字幕文本 | 融合进结构化笔记，不照搬 |

---

## 🚀 快速开始

### 1. 克隆安装

```bash
git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
cd bilibili-video-notes-skill
pip install -r scripts/requirements.txt
```

### 2. 安装 FFmpeg

系统环境变量中需要可直接调用 `ffmpeg`。

### 3.（可选）配置外部视觉 API

> 默认由 Agent 自身多模态识图完成选帧和提取，**这一步可以跳过**。
> 只有当你明确要改用外部视觉服务，或当前会话读不了图片、批量规模确实需要外部处理时，才配置这里。

```bash
cp .env.example .env
```

编辑 `.env`（只有 `VISION_API_KEY` 是真·敏感信息，必填）：

```bash
VISION_API_KEY=your_api_key_here
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
```

支持任何 OpenAI 兼容格式的多模态 API（SiliconFlow、OpenAI、本地 vLLM 等）。
`VISION_BASE_URL` / `VISION_MODEL` 是**运行参数**（这次调谁、调哪个模型），改动优先走命令行
`--base-url` / `--model`，不必动 `.env`。

### 4. 配置 B 站 Cookie（可以直接告诉AI让他代劳）

```bash
cp bilibili_cookies.txt.example bilibili_cookies.txt
```

从浏览器 F12 复制 `SESSDATA` 字段，替换文件中的 `YOUR_SESSDATA_HERE`。

> ⚠️ Cookie 有时效（通常几天），过期后需重新获取。
> 开工时把这份 cookie 复制到本轮的 `--workspace` 目录，脚本就是在那儿找它的。

### 5. 配置本机层路径

仓库本身不含任何绝对路径。复制模板并填上你这台机器的实际路径：

```bash
cp local.example.md local.<agent>.md
```

填四项：运行目录 / 帧图根（**必须纯英文路径**）/ 交给用户的成品目录 / 密钥目录。
`local.*.md` 已 git 忽略，不会被推走。详见 [AGENTS.md](AGENTS.md)。

---

## 🚀 详细使用教程

### 第一步：准备环境

#### 1.1 克隆仓库

```bash
git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
cd bilibili-video-notes-skill
```

#### 1.2 安装 Python 依赖

```bash
pip install -r scripts/requirements.txt
```

如果使用 Anaconda：

```bash
conda create -n bili-notes python=3.11
conda activate bili-notes
pip install -r scripts/requirements.txt
```

#### 1.3 安装 FFmpeg

本工具需要 `ffmpeg` 处理视频。

**Windows 安装方法**：
1. 下载：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
2. 解压到 `C:\\ffmpeg`
3. 把 `C:\\ffmpeg\\bin` 加到系统环境变量 PATH
4. 重新打开终端，验证：`ffmpeg -version`

**macOS**：
```bash
brew install ffmpeg
```

**Ubuntu/Debian**：
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

---

### 第二步：（可选）配置外部视觉 API

> 默认走 Agent 自身识图，不需要这一步。仅在选择外部视觉后备时配置。

复制示例文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
VISION_API_KEY=your_api_key_here
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
```

#### 常用 API 配置示例

**SiliconFlow（硅基流动，内置默认）**：
```bash
VISION_API_KEY=sk-...
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
```

**OpenAI**：
```bash
VISION_API_KEY=sk-...
VISION_BASE_URL=https://api.openai.com/v1
VISION_MODEL=gpt-4o
```

**本地 vLLM**：
```bash
VISION_API_KEY=not-needed
VISION_BASE_URL=http://localhost:8000/v1
VISION_MODEL=your-local-model
```

> ⚠️ 外部后备路径下**勿用 32B 模型**（排队严重，>75s 超时）。

---

### 第三步：配置 B 站 Cookie

B 站 AI 字幕需要登录态才能下载。

复制示例文件：

```bash
cp bilibili_cookies.txt.example bilibili_cookies.txt
```

获取 SESSDATA 的方法：

1. 用 Edge/Chrome 打开 [bilibili.com](https://www.bilibili.com) （确保已登录）
2. 按 `F12` 打开开发者工具
3. 点击 **Application**（应用程序）标签
4. 左侧 **Cookies** → `https://www.bilibili.com`
5. 找到 `SESSDATA`，复制它的值
6. 替换 `bilibili_cookies.txt` 里的 `YOUR_SESSDATA_HERE`

文件格式如下：

```
.bilibili.com  TRUE  /  FALSE  0  SESSDATA  你的SESSDATA值
```

> ⚠️ Cookie 通常有效期几天，过期后字幕下载会失败，需要重新获取。
> 脚本按「当前目录 → `$BILI_NOTES_WORKSPACE` → 脚本所在目录 → `~/bilibili-notes/workspace/`」
> 的顺序找它，**没有 `--cookies` 参数**——所以开工前先把 cookie 复制到 `--workspace` 目录。

---

### 告诉 AI 让它代劳配置

你不需要自己动手配置。把下面的提示词复制粘贴给 AI，它会帮你完成安装、配置，你只需要告诉他SESSDATA(如何获得SESSDATA可见上一步)。选择外部视觉后备时再额外提供 api、baseurl、模型名。

#### Kimi 版

```
首先，帮我完成初始化配置：
1. 克隆本仓库到当前工作目录：git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
2. 进入项目目录并安装依赖：pip install -r scripts/requirements.txt
3. 确保系统可以调用 ffmpeg（如果没有，请帮我安装并加入 PATH）
4. 从 bilibili_cookies.txt.example 复制出 bilibili_cookies.txt，然后问我要 B 站 SESSDATA，填入后给我确认
5. 复制 local.example.md 成 local.<agent>.md，问我要运行目录 / 帧图根（必须纯英文）/ 成品目录 / 密钥目录，填入后给我确认

初始化完成后，等待用户下一步指令，工作时按 AGENTS.md 执行笔记生成流程。

注意事项：
- 默认用你自己的多模态能力看截图，不要默认去调外部视觉 API
- 帧目录必须是纯英文路径
- 不要使用 vision_analyze 串行调用
- 笔记要融会贯通字幕和截图，宁可多写不可遗漏
```

#### Claude Code 版

```
首先做初始化配置：
1. git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
2. cd bilibili-video-notes-skill
3. pip install -r scripts/requirements.txt
4. 检查 ffmpeg 是否存在，不存在则帮我安装
5. cp bilibili_cookies.txt.example bilibili_cookies.txt，然后问我要 B 站 SESSDATA，填入后让我确认
6. 复制 local.example.md 成 local.<agent>.md，问我要四项本机路径，填入后让我确认

初始化完成后，等待用户下一步指令，工作时按 AGENTS.md 执行笔记生成流程。
```

#### Codex CLI 版

```
首先完成初始化配置：
1. git clone https://github.com/mokaluona/bilibili-video-notes-skill.git
2. cd bilibili-video-notes-skill
3. pip install -r scripts/requirements.txt
4. 确保 ffmpeg 可用
5. cp bilibili_cookies.txt.example bilibili_cookies.txt，然后问我要 B 站 SESSDATA，填入后让我确认
6. 复制 local.example.md 成 local.<agent>.md，问我要四项本机路径，填入后让我确认

初始化完成后，等待用户下一步指令，工作时按 AGENTS.md 执行笔记生成流程。
```

其实不是这三个Agent可也使用这套提示词，只需要把后面的“工作时按 xxx.md 执行笔记生成流程”删去即可

---

## 📖 配置好之后如何使用

当你已经完成以下配置：
- Python 依赖已安装
- `bilibili_cookies.txt` 中已填入有效的 SESSDATA
- ffmpeg 可在终端直接调用
- （仅走外部视觉后备时）`.env` 中已填入有效的 VISION_API_KEY / BASE_URL / MODEL

只需要告诉 AI一句话，它就会跟踪完整流程：

### Kimi 版

```
请帮我做这个视频的笔记：https://www.bilibili.com/video/BV1xx411c7mD

按照 AGENTS.md 流程执行，不要凭印象。
```

### Claude Code 版

```
请帮我做这个视频的笔记：https://www.bilibili.com/video/BV1xx411c7mD

已配置好 bilibili_cookies.txt，按照 AGENTS.md 执行。
```

### Codex CLI 版

```
请帮我做这个视频的笔记：https://www.bilibili.com/video/BV1xx411c7mD

已配置好 bilibili_cookies.txt，按照 AGENTS.md 执行。
```

不是这三个Agent可也使用这套提示词，让他按照 AGENTS.md 流程执行，不要凭印象即可

### 笔记生成流程

AI 会自动执行以下步骤（细节以 [`AGENTS.md`](AGENTS.md) 为准）：

1. **先定档位**：花 30 秒摸视频（字幕条数 + 抽 3 帧看画面密度），建议精读 / 过一遍 / 总结，让你确认
2. **抽帧**：`extract_frames.py --mode scene --backup-interval 30` 下载视频、字幕，抓 PPT 翻页 + 每 30 秒保底
3. **去重**：`smart_select.py` 用 OCR + 哈希去重，129帧 → 20-40帧
4. **选帧**：先读字幕形成知识点清单，再用联系表定位候选帧；最终帧逐张打开原图核对
5. **识图**：Agent 自身多模态提取图中文字/公式/表格/概念/因果链，结果存 `vision_extract*.json`
6. **提取字幕关键因果句**：`extract_key_sentences.py` 提取字幕中必须保留的 WHY 解释句
7. **生成骨架**：`generate_config_draft.py` 从提取结果 + 字幕自动生成 DOCX 配置骨架，再人工润色
8. **样本先行**：先出 `sample.docx` 检查字体、表格和截图图注，确认可渲染后再生成全文
9. **验证**：`verify_docx.py --type <lecture|opinion|vlog> --subtitle` 按视频性质检查格式和字幕因果句覆盖率
10. **清理**：可再生的中间产物**删到回收站**，保留字幕和提取结果

### 查收结果

AI 执行完毕后，你应该在本轮的运行目录（`<RUN_DIR>/work/<内容名>/`）看到：

```
work/<内容名>/
├── <BV>_p<N>_subtitles.txt      # 字幕文本（保留）
├── vision_extract_pXX.json      # 图中内容提取结果（保留，可复用原料）
├── checklist_pXX.json           # 知识点覆盖清单
└── X.X_章节标题_v1.docx          # 最终笔记（成品会再交付到成品目录）
```

如果一切正常，直接打开 DOCX 查看即可。

---

### 手动微调（如需要）

AI 生成的 DOCX 可能需要你微调：
- 某些帧可能选得不太好，可以替换
- 正文部分可能需要根据你的理解补充
- 排版风格可以在 `templates/docx_note_v2.py` 中调整

---

## 📖 完整工作流

```
scene 抽帧 + 30s 保底（PPT 翻页 + 兜底）
  ↓ OCR 预筛：去掉空白/面部帧
  ↓ 哈希去重（视觉结构相似归为一组）→ 20-40 帧
  ↓ 读字幕建知识点清单 → 联系表定位候选帧
  ↓ Agent 自身识图（外部 API 仅后备）：提取文字/公式/表格/概念
  ↓ 生成 DOCX 骨架 → 人工润色
  ↓ 样本预检（sample.docx）→ 生成全文 → 渲染
  ↓ 覆盖率验证 → 回收站清理中间产物
```

### 为什么要分「定位候选」和「提取内容」两步？

| 步骤 | 看的帧数 | 输出内容 | 目的 |
|------|----------|------------|------|
| 定位/评分 | 20-40 | theme/keywords/score/complete | 选帧 |
| 提取 | 7-12 | 图中完整文字/公式/表格/概念 | 写正文 |

分开可以最小化总 token 和外部 API 成本（走外部后备时），同时避免用任何平台的 `vision_analyze` 串行调用。

---

## 🔧 命令参考

> 本节的流程以 [`AGENTS.md`](AGENTS.md) 为准；两边不一致时**以 `AGENTS.md` 为准**。

### 1. 抽帧

```bash
python scripts/extract_frames.py BV1xx411c7mD \
  --page 1 \
  --mode scene --backup-interval 30 \
  --subtitle \
  --workspace ./work/<内容名> \
  --frames ./frames/pXX
```

### 2. 去重

```bash
python scripts/smart_select.py ./frames/pXX/fixed \
  --output-dir ./frames/pXX/selected \
  --skip-clustering
```

### 3.（可选）并发打分（外部后备）

> 自身识图时跳过这一步；候选已经明确时也跳过。

```bash
python scripts/score_frames_concurrent.py \
  --frames ./frames/pXX/selected \
  --output ./work/<内容名>/vision_scores_pXX.json \
  --workers 8
```

### 4.（可选）自动推荐选帧

`recommend_frames.py` 按打分自动推荐 Top 10 并复制到 `final/`；人工只需确认这 10 帧，要调整再从 `selected/` 补。
自身识图时直接按知识点选 `final/`。

```bash
python scripts/recommend_frames.py \
  --scores ./work/<内容名>/vision_scores_pXX.json \
  --frames ./frames/pXX/selected \
  --output ./frames/pXX/final \
  --top 10 --auto-copy
```

### 5.（可选）提取图中内容（外部后备）

```bash
python scripts/score_frames_concurrent.py \
  --frames ./frames/pXX/final \
  --output ./work/<内容名>/vision_extract_pXX.json \
  --mode extract \
  --workers 1 --resume
```

### 6. 生成 DOCX

```bash
# 先自动生成配置骨架,再人工润色
python scripts/generate_config_draft.py \
  --vision ./work/<内容名>/vision_extract_pXX.json \
  --title "章节标题" --source "来源说明" \
  --frames-dir ./frames/pXX/final \
  --output ./work/<内容名>/config_pXX_draft.json
python templates/gen_docx_dynamic.py --config ./work/<内容名>/config_pXX_draft.json
```

### 7. 验证

```bash
python scripts/verify_docx.py ./work/<内容名>/<output>.docx \
  --type lecture --subtitle ./work/<内容名>/<BV>_p<N>_subtitles.txt
```

`--type` 按视频性质选，选错会把合格的笔记判成 FAIL：`lecture` 讲课/教程（阈值 75%）、
`opinion` 经验分享/观点谈（阈值 50%，先滤口头禅）、`vlog` 杂谈（不查覆盖率）。

### 8. 清理

删除走**回收站**，不做永久删除。要清的只有可再生的中间产物：

```powershell
# 把目标文件删到回收站（不是永久删除）
Add-Type -AssemblyName Microsoft.VisualBasic
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('.\work\<内容名>\BV1xx411c7mD_p1.mp4','OnlyErrorDialogs','SendToRecycleBin')
```

保留：字幕.txt、vision_extract_pXX.json、checklist_pXX.json —— mp4 / wav / 帧图 / scores.json 清掉（可重生成）
**判断不出该不该删的，一律保留。**

---

## ⚙️ 配置参数

| 环境变量 / 参数 | 说明 | 示例 |
|---|---|---|
| `.env` | 外部视觉 API 配置（仅后备时需要） | 见 `.env.example` |
| `--workspace` | 工作区目录 | `./work/<内容名>` |
| `--frames` | 帧输出目录 | `./frames/pXX` |
| `--page` | B 站分P页码 | `1` |
| `--mode scene` | 按画面切换点抽帧（**默认走这个**） | - |
| `--mode cover` | 每10秒抽一帧（仅画面连续变化时用） | - |
| `--backup-interval 30` | scene 模式下的保底间隔（秒） | `30` |
| `--skip-clustering` | 保留所有去重帧 | - |
| `--workers` | 并发线程数 | 打分 `8` / 提取 `1` |
| `--mode extract` | 从图中提取完整内容 | - |
| `--type` | 验证时的视频性质 | `lecture` / `opinion` / `vlog` |

---

## 🛠️ 常见问题

### B 站限流（HTTP 412）

```bash
# 降级到 480p + 加 User-Agent
yt-dlp --user-agent "Mozilla/5.0 ..." -f "bestvideo[height<=480]+bestaudio/best[height<=480]" ...
```

### Cookie 过期

字幕下载失败但视频下载成功 → 先跳过字幕，后面补：

```bash
python scripts/extract_frames.py BV号 --page N --subtitle --no-download --mode fixed --interval 9999
```

### 帧目录必须是纯英文路径

AI 视觉工具可能无法识别中文路径。

### 帧太多 / API 调用太贵

129帧 → 用 `smart_select.py --skip-clustering` 压到 20-40帧，再送 AI 打分，省 60%-80% API 调用。
默认走 Agent 自身识图时，这一步省的是你自己的上下文，价值同样成立。

### Vision 选到了半成品截图

默认路径下，最终帧由 Agent 逐张打开原图核对。走外部后备时，打分 prompt 已内置强调：
**"Among visually similar frames, pick ONLY the MOST COMPLETE version"**。

### 笔记被判 FAIL，但内容其实没问题？

`verify_docx.py --type` 选错了。经验分享类视频的关键句多是口语碎片，按 `lecture` 口径打容易差一两个点误判，
按视频性质选 `opinion` / `vlog`。

---

## 🤖 Agent 使用

**项目指令的唯一真源是 [`AGENTS.md`](AGENTS.md)**，其余三个文件都是指向它的指针：

### Kimi

读取 `SKILL.md`（指针），按 `AGENTS.md` 的流程执行。

### Claude Code

`CLAUDE.md` 会被自动加载为项目指令（指针）。

### Codex CLI

`AGENTS.md` 会被自动加载为项目指令。

---

## 📁 目录结构

```
bilibili-video-notes/
├── AGENTS.md                   # 项目指令唯一真源
├── README.md                   # 本文件
├── SKILL.md                    # Kimi / 通用 skill 入口（指针）
├── CLAUDE.md                   # Claude Code（指针）
├── CONTRIBUTING.md             # 贡献指南（指针）
├── local.example.md            # 本机层配置模板 → 复制成 local.<agent>.md
├── .env.example                # 视觉 API 配置模板 → 复制成 .env
├── .gitignore
├── bilibili_cookies.txt.example
├── scripts/
│   ├── extract_frames.py
│   ├── smart_select.py
│   ├── quick_dedup.py
│   ├── score_frames_concurrent.py
│   ├── recommend_frames.py
│   ├── extract_key_sentences.py
│   ├── generate_config_draft.py
│   ├── verify_docx.py
│   ├── verify_checklist.py
│   ├── clean_markdown_bold.py
│   └── requirements.txt
├── templates/
│   ├── gen_docx_dynamic.py
│   ├── docx_note_v2.py
│   ├── config_example.json
│   ├── env.example             # 旧路径模板，保留兼容；新配置请用根目录 .env.example
│   └── checklist.json
├── video_notes/                # 模块化笔记工具包（实验性，见下）
└── tests/                      # video_notes 的 unittest 测试套件
```

**`local.<agent>.md` 不进 git** —— 每台机器、每个 agent 自己的路径写在那里，
仓库本身不含任何绝对路径。

---

## 🔀 相对上游的改进

本仓库 fork 自 [asdhabdua/bilibili-video-notes-skill](https://github.com/asdhabdua/bilibili-video-notes-skill)，
在其基础上做了以下改动：

### 1. 视觉识别默认改为「Agent 自身多模态」

上游默认调用外部 OpenAI 兼容视觉 API 打分和提取。本仓库把**Agent 自己识图**作为默认路径：
GPT / Codex、Kimi 直接用当前会话的多模态能力完成选帧、文字、公式、表格、手写批注识别，
结果写入兼容下游字段的 `vision_extract*.json`（附 `recognition_source: "agent_native"` 和图像 SHA-256）。
外部 API 降为**可选后备**——只有你明确指定，或当前会话读不了图片时才走。
这去掉了对外部服务排队、限流和模型规格的依赖。

### 2. 三档方案（先定档位再动手）

档位不是视频属性，而是"这次拿它做什么"：

| 档位 | 适用场景 | 耗时 |
|---|---|---|
| 第一档·精读 | 讲课课件要复习 | ~5 分钟 / 20min 视频 |
| 第二档·过一遍 | 口播 + 少量图 | 5~8 分钟 |
| 第三档·总结 | 不读原文只要结论 | 1~2 分钟 |

### 3. 生成与审核分离：`video_notes/` 模块化工具包

新增 `video_notes/` 包和 `tests/` 测试套件，把流程拆成可校验的阶段：

- **阶段机**：`preflight → acquire → 去重 → 候选 → 视觉审核 → 正文 → 内容审核 → 样本/生成 → 渲染 → 页面审核 → 校验 → 交付 → 清理`
- **审核留痕**：审核记录带 `reviewer {kind, id, independence}`，按内容哈希拒绝过期结果；
  Agent 不能自称"独立审核"
- **质量报告**：逐项检查正文契约、来源冻结、当前构建/渲染、四类审核、逐字匹配、档位支持，输出
  `blocked / ready_with_disclosure / ready`
- **并发额度**：下载/CPU、外部提取、Word 渲染各自用本地锁目录限流，不抢占僵尸锁
- **回收站清理**：只回收登记过的临时素材，未登记的未知文件一律保留
- **CLI 入口**：`python -m video_notes <子命令>`（`run` / `build-run` / `render` / `validate` / `deliver` / `cleanup` 等）

> ⚠️ 该工具的 schema 目前是 **experimental**，尚未完成两次真实视频任务的端到端验收。
> 日常使用仍以 `AGENTS.md` 的手动流程为准。

### 4. 文档改为「单一真源 + 指针」

上游 `SKILL.md` / `CLAUDE.md` / `CONTRIBUTING.md` 各自维护一份正文，容易彼此漂移。
本仓库把**唯一真源收敛到 `AGENTS.md`**，其余三个文件降为几行的指针，改规矩只改一处。

### 5. 本机层路径从仓库抽离

新增 `local.example.md`；仓库不再含任何绝对路径，每台机器各维护一份 git 忽略的
`local.<agent>.md`。密钥规则同时写清：`bilibili_cookies.txt`（存放地 `SECRETS_DIR`，读取地是工作目录）
与 `.env`（放仓库根）**存放地不同**，因为脚本读法不同。

### 6. 新增可复用脚本

- `scripts/recommend_frames.py` — 按打分自动推荐 Top 10 并复制到 `final/`
- `scripts/generate_config_draft.py` — 从提取结果 + 字幕自动生成 DOCX 配置骨架
- `scripts/quick_dedup.py` — 快速去重
- `templates/gen_docx_dynamic.py` + `templates/config_example.json` — 数据驱动的 DOCX 生成器

### 7. 抽帧默认改 `scene + 30s 保底`

`--mode scene --backup-interval 30` 替代全覆盖 `--mode cover`：抓 PPT 翻页 + 每 30 秒兜底，
23 分钟视频约 30 帧，比全覆盖少约 67%。

### 8. 验证器按视频性质分档

`verify_docx.py --type` 决定覆盖率阈值：`lecture` 75%、`opinion` 50%（先滤口头禅）、`vlog` 不查。
无字幕时自动跳过覆盖率检查。

### 9. 清理改走回收站

删除一律走回收站（`Microsoft.VisualBasic` SendToRecycleBin），不做永久删除；
未登记的未知文件一律保留。

### 10. 修掉会让流程静默失效的脚本缺陷

上游有四处导致流程安静出错（无报错但结果不对）的缺陷，已修。

---

## 📄 License

MIT License - 自由使用和修改。

## 🙏 致谢与来源

本项目 fork 自 **[asdhabdua/bilibili-video-notes-skill](https://github.com/asdhabdua/bilibili-video-notes-skill)**，
原始设计与实现归原作者所有，感谢其开源。

上游用到的开源组件：

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [RapidOCR](https://github.com/RapidAI/RapidOCR) - OCR 文字识别
- [ImageHash](https://github.com/JohannesBuchner/imagehash) - 感知哈希
- [python-docx](https://github.com/python-openxml/python-docx) - DOCX 生成

## 📬 反馈与建议

- **本 fork 的问题/建议**：[GitHub Issues](https://github.com/mokaluona/bilibili-video-notes-skill/issues/new)
- **上游原项目的问题**：请提到 [上游仓库](https://github.com/asdhabdua/bilibili-video-notes-skill/issues)

欢迎提交 Issue 和 PR！如果觉得有用的话欢迎点一下星标哟🤗
