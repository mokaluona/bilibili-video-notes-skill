# 本机层配置（模板）

把这份复制成 `local.<agent>.md`（例如 `local.kimi.md`），填上**你这台机器、你这个 agent**
的实际路径。`local.*.md` 已进 `.gitignore`，**不会进 git、不会被推走**。

仓库本身不含任何绝对路径 —— 所有路径都从这份文件读。换机器、换 agent 只改这一份。

## 四项

```yaml
RUN_DIR:        # 本轮运行目录。每轮新建一个，中间产物全落在它下面
FRAMES_ROOT:    # 帧图根目录。必须纯英文路径 —— 视觉工具不认中文
DELIVERY_DIR:   # 成品交付目录。成品按内容类型分子文件夹放在这里
SECRETS_DIR:    # bilibili_cookies.txt 所在目录。不进 git（.env 放仓库根，模板见 .env.example）
```

参考写法（**下面是占位示例，按自己的实际情况填**）：

```yaml
RUN_DIR:        D:\AppData\<agent>\tasks\<日期>\<运行ID>
FRAMES_ROOT:    D:\AppData\<agent>\frames
DELIVERY_DIR:   <用户桌面>\AgentVedioWord
SECRETS_DIR:    D:\AppData\<agent>\secrets
```

## 环境变量（脚本侧）

脚本不读这份 markdown，读环境变量；两个都不设时回落 `~/bilibili-notes/`：

| 环境变量 | 含义 | 对应上面哪一项 |
|---|---|---|
| `BILI_NOTES_WORKSPACE` | 中间产物根 | `RUN_DIR` |
| `BILI_NOTES_FRAMES` | 帧图根 | `FRAMES_ROOT` |

命令行里的 `<RUN_DIR>` / `<FRAMES_ROOT>` / `<DELIVERY_DIR>` 占位，按这份文件里的实际值替换。

## 想少写几次？

在本机 `local.<agent>.md` 里额外记一行「日常跑法」，比如常用 BV 号、默认档位，
下次直接照抄，不用重新拼命令。
