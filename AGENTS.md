# Bilibili Video Notes —— 项目真源

从 B 站教育/讲课视频生成带截图的 DOCX 学习笔记。
全流程：下载视频 + 字幕 → 抽帧 → OCR 去重 → 视觉打分选帧 → 提取图中内容 → 融合生成 DOCX。

> 本文件是项目的**唯一真源**。`SKILL.md` / `CLAUDE.md` / `CONTRIBUTING.md` 都是指向这里的**指针**——
> 改规矩只改这一份，别处不用动。（手抄的副本会赢过真源，这个项目自己踩过。）

## 规矩只读，代码可写

- **规矩**：`AGENTS.md`、`README.md`、`CONTRIBUTING.md` —— 任何 agent 只读，要改先问用户。
- **代码**：`scripts/`、`templates/` —— 可以改（修 bug、加参数）。
- 规矩文件带只读属性（`attrib +R`），那是**可见性提示不是锁**：`git pull` 需要能写它们，所以不做 ACL。

## 路径：看本机层文件，绝不写进仓库

**本仓库不含任何绝对路径。** 每台机器、每个 agent 各维护一份 git 忽略的 `local.<agent>.md`，
照 `local.example.md` 抄，填四项：

| 项 | 含义 |
|---|---|
| `RUN_DIR` | 本轮运行目录，每轮新建；所有中间产物落在它下面 |
| `FRAMES_ROOT` | 帧图根目录，**必须纯英文路径**（视觉工具不认中文路径） |
| `DELIVERY_DIR` | 成品交付目录（成品按内容类型分子文件夹） |
| `SECRETS_DIR` | `bilibili_cookies.txt` 的**正式副本**所在目录，**不进 git**（`.env` 不在那儿，见下） |

脚本侧读环境变量 `BILI_NOTES_WORKSPACE`（中间产物根）、`BILI_NOTES_FRAMES`（帧图根）；
两者都不设时回落 `~/bilibili-notes/`。下面命令里的 `<RUN_DIR>` / `<FRAMES_ROOT>` 等占位，
按你自己 `local.<agent>.md` 里的实际值替换。

### 密钥：脚本实际从哪找

`SECRETS_DIR` 是**存放地**，不是脚本读取地——两者不一样，先看清：

- **`bilibili_cookies.txt`** —— 按「当前目录 → `$BILI_NOTES_WORKSPACE` → 脚本所在目录 →
  `~/bilibili-notes/workspace/`」的顺序找，找不到直接报错。
  **没有 `--cookies` 参数可传。** 所以每轮开工前，先把 `SECRETS_DIR` 里那份
  **复制到 `--workspace` 指向的目录**（即 `<RUN_DIR>/work/<内容名>/`）——它就在那儿找。
- **`.env`（视觉 API 配置）** —— 只从**脚本所在目录**加载（= 仓库根）；那儿没有才退回进程环境变量
  `VISION_API_KEY` / `VISION_BASE_URL` / `VISION_MODEL`。

**`.env` 就放本仓库根目录**，`bilibili_cookies.txt` 则留 `SECRETS_DIR` —— 两者存放地不同，
原因是脚本读法不同（cookies 能顺着工作目录找，`.env` 只认脚本旁边）。

- 仓库里进 git 的是 `.env.example`（只有键名），真值在 `.env`，已被 `.gitignore` 挡住。
  这是**本地开发的通行规范**（Django / Rails / Node 都这么发）。
- `VISION_BASE_URL` / `VISION_MODEL` 是**运行参数**（这次调谁、调哪个模型），会变；
  改它们优先用**命令行** `--base-url` / `--model`，不必动 `.env`。
  不做成全局环境变量：那是机器级配置，会污染全局状态、且被每个子进程继承。

密钥规矩不变：**只读路径、不读内容、不贴进聊天、不进 git。**

## 三档方案（先定档位再动手）

档位不是视频的属性，而是"这次拿它做什么"。判定 = 字幕完整度 × 视觉信息密度 × 阅读需求。

| 档位 | 适用场景 | 流程 | 耗时 |
|---|---|---|---|
| 第一档·精读 | 讲课课件要复习 | scene + 30s 保底抽帧 → 去重 → 打分 → 推荐选帧 → 提取 → **骨架生成** → 人工润色 → DOCX | ~5 分钟 / 20min 视频 |
| 第二档·过一遍 | 口播 + 少量图，自己看 | 字幕为主 + 每章 1~2 帧字幕定位截图 | 5~8 分钟 |
| 第三档·总结 | 不读原文只要结论 | 纯字幕 → LLM 结构化总结（章节+要点+结论） → Markdown | 1~2 分钟 |

用户口头标注档位时按标注执行；未标注 → 花 30 秒摸视频（字幕条数 + 抽 3 帧看画面密度），
自动建议档位后让用户确认。

## 目录规范

- 中间产物（字幕、中间 JSON、工作脚本）→ `<RUN_DIR>/work/<内容名>/`
- 帧图 → `<FRAMES_ROOT>/<英文>/`；去重结果进 `selected/`，最终选中帧进 `final/`
- 成品 → `<DELIVERY_DIR>/<内容类型>/`，与已有笔记平级
- 截图 → `<交付目录>/<内容类型>/attachment/<内容名>/`，笔记里用相对路径
  `![](attachment/<内容名>/x.jpg)` 引用。**禁止**把图片散放在笔记旁或内容文件夹里。
- 内容名按视频内容命名，**禁** `work1` / `work2` 这类编号；目录层级**两层封顶**。
- 交付目录根若有 `目录规范.md`，**写入前必读**。

**中间产物清理——留原料、删可再生的：**

| 留 | 删 |
|---|---|
| 字幕 `txt` / `json` | `*.mp4`（重下十几秒） |
| `vision_extract.json`（花了钱和时间的唯一原料） | `*.wav` / `*.m4a`（ASR 中间件，单个 55–95 MB） |
| `*.asr.jsonl`、工作脚本 | 抽帧图片、`scores.json`（重跑约 20 秒） |
| **任何判断不出的东西** | |

删除走回收站，不做永久删除。

## 使用方法（第一档·精读）

```bash
# 0. 先定档位（见上）

# 1. 下载视频 + 字幕（scene 检测 PPT 翻页 + 每 30 秒保底）
python scripts/extract_frames.py <BV号> \
  --page <N> --mode scene --subtitle --backup-interval 30 \
  --workspace <RUN_DIR>/work/<内容名> \
  --frames <FRAMES_ROOT>/<英文>

# 2. OCR + 感知哈希去重
python scripts/smart_select.py <FRAMES_ROOT>/<英文>/scene \
  --output-dir <FRAMES_ROOT>/<英文>/selected \
  --skip-clustering

# 3. 并发打分（换提供方 / 换模型就加 --base-url / --model，否则用 .env 里的默认值）
python scripts/score_frames_concurrent.py \
  --frames <FRAMES_ROOT>/<英文>/selected \
  --output <RUN_DIR>/work/<内容名>/vision_scores_p<NN>.json \
  --workers 8 \
  --base-url https://api.siliconflow.cn/v1 --model Qwen/Qwen3-VL-8B-Instruct

# 4. 按分数推荐 Top 10，自动复制到 final/
python scripts/recommend_frames.py \
  --scores <RUN_DIR>/work/<内容名>/vision_scores_p<NN>.json \
  --frames <FRAMES_ROOT>/<英文>/selected \
  --output <FRAMES_ROOT>/<英文>/final \
  --top 10 --auto-copy
# 人工确认：要调整就从 selected/ 直接复制其他帧到 final/

# 5. 串行提取（小图 768 宽，+ 断点续传）
python scripts/score_frames_concurrent.py \
  --frames <FRAMES_ROOT>/<英文>/final \
  --output <RUN_DIR>/work/<内容名>/vision_extract_p<NN>.json \
  --mode extract --workers 1 --resume

# 6. 提取字幕关键因果句
python scripts/extract_key_sentences.py \
  <RUN_DIR>/work/<内容名>/<BV>_p<N>_subtitles.txt

# 7. 自动生成 DOCX 骨架配置（替代从零手写）
python scripts/generate_config_draft.py \
  --vision <RUN_DIR>/work/<内容名>/vision_extract_p<NN>.json \
  --key-sentences <RUN_DIR>/work/<内容名>/<BV>_p<N>_subtitles.txt.key.json \
  --title "章节标题" \
  --source "来源说明" \
  --frames-dir <FRAMES_ROOT>/<英文>/final \
  --output <RUN_DIR>/work/<内容名>/config_p<NN>_draft.json
# 人工润色：调整顺序、补充细节、删减冗余

# 8. 生成 DOCX
python templates/gen_docx_dynamic.py \
  --config <RUN_DIR>/work/<内容名>/config_p<NN>_draft.json
# 产物 → <DELIVERY_DIR>/<内容类型>/

# 9. 验证 + 清理
# --type 按视频性质选，选错会把合格的笔记判成 FAIL：
#   lecture 讲课/教程（阈值 75%）、opinion 经验分享/观点谈（阈值 50%，先滤口头禅）、
#   vlog 杂谈（不查覆盖率）
# 无字幕时自动跳过覆盖率检查，失败时按优先级输出缺失句
python scripts/verify_docx.py <交付的 docx> \
  --type <lecture|opinion|vlog> --subtitle <RUN_DIR>/work/<内容名>/<BV>_p<N>_subtitles.txt
```

## 字幕获取

- `https://api.bilibili.com/x/web-interface/view?bvid=` 拿 cid
- `https://api.bilibili.com/x/player/wbi/v2?bvid=&cid=`，带 SESSDATA cookie，
  从 `data.subtitle.subtitles[0].subtitle_url` 拿 ai-zh 字幕 —— **可靠方式**
- yt-dlp `--write-subs` 和 `player/v2` 接口对部分视频拿不到字幕
- cookie 是 Netscape 格式（仅含 SESSDATA）
- `bilibili_cookies.txt` 放 `SECRETS_DIR`；`.env` 放仓库根（见上文「密钥：脚本实际从哪找」）。
  两者都：**不读内容、不贴进聊天、不进 git**

## 笔记写作标准

- 以顶级学者身份，融会贯通字幕和截图
- 追求知识完整性，宁可多写不可遗漏
- 保留所有重要细节、公式、定义、例题、做题技巧
- 解释 WHY，不只是 WHAT；不带时间戳
- 截图只补充字幕没讲的考点，不抄非考点内容

## 关键规则与经验

- **抽帧 `--mode scene --backup-interval 30`**：讲课/翻页式视频用这个。scene 抓 PPT 翻页 +
  每 30 秒保底，23 分钟视频约 30 帧需人工看，比 cover 少 67%。cover 只用于画面连续变化的视频。
- **选帧 `recommend_frames.py`**：打分后自动推荐 Top 10，人工只看 10 帧。
- **骨架生成 `generate_config_draft.py`**：从 `vision_extract.json` + 字幕自动生成 DOCX 配置骨架，
  人工只需润色。
- **验证 `verify_docx.py`**：`--type` 决定覆盖率阈值——lecture 75%、opinion 50%（滤口头禅）、vlog 不查。
  经验分享类视频的关键句多是口语碎片，按 lecture 口径打容易差一两个点误判，**按视频性质选对类型**；
  无字幕时跳过覆盖率检查。
- 视觉模型用 SiliconFlow `Qwen/Qwen3-VL-8B-Instruct`（约 2s/帧）；**勿用 32B**（排队严重，>75s 超时）。
- SiliconFlow 限流：打分 `--workers 8` 可以；**提取必须串行（`--workers 1`）+ 增量存盘 + 失败跳过**。
- 所有视觉分析走 `score_frames_concurrent.py`，不要用串行 `vision_analyze`。
- ffmpeg 9.x：脚本已适配 `-fps_mode vfr`（替代废弃的 `-vsync`）。
- DOCX 用 `run.bold` / `run.font.color`，不用 `**xxx**` 等 markdown 语法。
- 交付：最终产物用 `computer://` 链接（指向用户可见目录）；中间产物不给链接。

## 依赖

```bash
pip install yt-dlp imagehash rapidocr-onnxruntime python-docx Pillow requests python-dotenv
```

需要 ffmpeg。

## 更新

```bash
git pull               # 取最新
git push origin main   # 改完代码记得推；规矩文件不要改
```
