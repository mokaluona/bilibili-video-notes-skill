# video_notes 使用接口

本文件记录 `video_notes/` 工具对外的接口约定：路径限制、等待参数、交付状态文件与恢复规则。
流程与政策以 [`../AGENTS.md`](../AGENTS.md) 为准，本文件只讲怎么用、报错怎么读。

## 路径限制

以下位置在每次交付、清理前都会被检查，任何**路径组件**（含该根目录自身）带符号链接或
reparse 点（junction、同步目录的重解析点）都会被拒绝：

| 检查对象 | 位置 |
|---|---|
| 交付根、交付目标、交付认领文件 | `deliver()`、`retention.plan()` |
| `workspace` / `frames` 根 | `retention.plan()` 清理前 |

报错含义：

- `Path escapes intended root` / `Resolved path escapes intended root` —— 路径落在允许的根之外。
- `Link or reparse component prohibited: <组件>` —— 该组件是链接或 reparse 点。

所以 `workspace`、`frames`、`delivery` 请用**普通本地目录**。同步盘（如 OneDrive）和 junction
可能不支持；能否可用以实际预检为准，不要假定某类路径一定被接受或一定被拒绝。

该检查**降低但不消除** TOCTOU 竞争（检查与真正的打开/删除之间仍有窗口）；清理脚本在删除前
会重新校验哈希，但工具不声称已证明所有操作系统竞争场景安全。

## 等待参数

`run_lock_timeout`（运行配置项，可写在 RunSpec 或机器配置里；单位秒）：

- **默认 `0`** —— 同一 `workspace` 已有任务持有变更锁时**立即失败**（`TimeoutError`），不等待。
- **正数** —— 允许有限等待；到期仍未拿到锁同样 `TimeoutError`。

它只控制**等待**，不抢占他人在用的锁，也不会接管陈旧锁。同一线程内重入同一 `workspace` 不会
重复加锁。这与资源锁（`quota`）的等待是两个独立参数。

## 交付状态文件

| 文件 | 含义 |
|---|---|
| `<workspace>/delivery-attempt.json` | 本次尝试的**意图与进度**：`attempt_id`、`plan`、`status`、`staged`、`published`，失败时另有 `reason` |
| `<workspace>/delivery-result.json` | **成功凭据**。存在即代表交付完成（含 `marker`、`attempt_id`、`files`，登记失败时含 `warnings`） |
| `<workspace>/delivery-failure.json` | 连状态文件都写不进去时的兜底记录：`primary_error` 与 `recording_error` |
| `<交付目录>/<输出名>.docx.delivery.json` | **发布认领 + 状态**。只有 `status=delivered` 代表完整成品；`staging` / `publishing` / `incomplete` 都不代表完成 |

发布顺序固定为：**先写 journal（意图）→ 再独占创建 marker（`open('x')`，取得发布权）→ 发布附件
→ 文档最后落盘**。附件与文档之间不是原子事务，工具也不这样承诺。

留在成品旁的 `.delivery.json` 是交付凭据，**不参与清理**，会一直保留。

## 恢复

`deliver --recover` 的条件（全部满足才继续）：

- 计划与当前 `plan()` 一致；
- 存在 marker 且其 `attempt_id` 与 journal 一致；
- 尚无 `delivery-result.json`。

恢复只复用本次已记录且哈希一致的暂存文件；**不覆盖**用户改过的内容，也不自动删文件回滚。

两种失败要分开看：

- **有 journal、无 marker** —— 该尝试从未取得发布权，**不可恢复**，直接重跑 `deliver`（不加 `--recover`）。
- **有 marker、无 journal，或 marker 归属不明** —— 工具**不接管、不删除**，也不自动判为过期。先查清
  对应任务、进程与磁盘状态再决定；自动接管会把恢复问题变成并发写入风险。

`--until deliver` / `--until completed` 遇到 `delivery-attempt.json` 而未见 `delivery-result.json`
时会停在 `needs_attention`，不会把半成品当作完成。

## 清理

只有 `delivery-result.json` 为 `delivered`、marker 状态一致、且各文件哈希未变时，才允许生成清理计划。
实际删除走回收站（`recycle.ps1`），删除前重新校验哈希与 reparse 组件，**不做永久删除**。
