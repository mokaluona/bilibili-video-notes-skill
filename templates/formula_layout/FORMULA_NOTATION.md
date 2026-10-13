# 公式输入与解析诊断

正文、表头、单元格和公式块仍共用 add_text。现有调用方可以忽略返回值，生成行为不新增报告或质量门。

parse(text, domain) 恒定返回 ParseResult(nodes, notices)，不再支持 strict。预期的格式错误返回 error Notice，并保留整段原文，不产生部分错误公式树。非字符串输入属于调用错误，仍抛 TypeError。

add_text 返回 notices；已有普通上下标与补事件使用现有 Word 发射器。新增 nary 识别节点不送入发射器，而按原文输出并返回 warning。第二步不实现原生积分或求和 OMML，不改变数学字体与颜色。

## 输入与兼容性

| 输入 | 第二步行为 |
|---|---|
| A^c、A^{c}、A^C、A^cB^c | 补事件横线保持支持 |
| A_i、A_{ij}、x^2、x^{n+1}、p^(n−k) | 原上下标保持支持 |
| x^2y、A^cost | AMBIGUOUS_SCRIPT error；显式写 x^{2}y 或合适的括号 |
| A^{}、A_{} | EMPTY_SCRIPT error，不生成空上下标 |
| A_{ij、A^{n+1 | UNCLOSED_GROUP error |
| A^{cc} | INVALID_DOMAIN_ARGUMENT error，不能把部分参数当补事件 |
| ∫_{x}^{2}{x e^{-y}} dy | 识别上下限与主体，UNSUPPORTED_NARY warning，输出仍为原文 |
| ∫_0^1 dy | LEGACY_NARY_BODY warning；目标写法为 ∫_{0}^{1}{1} dy |
| ∫_{0}^{1}{} dy | EMPTY_NARY_BODY error |

Σ、∑、∫、∬ 由词法级 operators 表统一识别，与 domain 无关。上下限和主体先做语法校验，主体中的畸形表达式不能因算子尚不支持而降级为 warning。嵌套主体通过紧邻花括号吸收，不猜测 dy 的边界。算子表记录后续发射需要的 chr、limLoc，但解析器不依赖 Word、docx 或 OMML 发射代码。

裸下划线和填空线可作为普通文字保留；发现数学操作数后的畸形记号会报错。若 c 确实是指数而非补事件，用 generic 域；注册 domain 仍只负责后缀语义。

## Notice 与坐标

规范字段是 code、severity、block_id、sub_path、text_span、message。错误码集合位于 operators.NOTICE_CODES。Parser 的 block_id 为 None、sub_path 为空；调用方通过 notices.locate 或 add_text 的可选参数补齐。

diagnose_runs 按原顺序直接拼接 run 的 text，不插入空格，再统一解析。text_span 是合并文本的 Unicode 字符左闭右开区间。表格使用渲染行 row/col：headers 为 row0，模型 rows[i] 为 row i+1。列表 item 从0开始。add_text 的 text_offset 可将单个输入的偏移映射到合并文本；跨 run 的公式应先合并再解析，不能各段单独猜测。

结构报告落盘、模板预检和质量门接线已按补充要求推迟到第四步。第二步的返回 notices 并不自动阻止旧模板交付；调用方消费报告前，这一点必须明确披露。

回归测试使用 python -m unittest discover -s tests。第一步 current_parser_snapshot 继续作为历史材料保存，新行为由 test_formula_diagnostics 验收，不再要求解析器复现错误快照。

## 第二步 Review 修复与语法边界

暂时保留有上下限的 Greek Σ 的旧 sub/sup 可见排版，同时继续返回 UNSUPPORTED_NARY warning。这里只复用既有节点，不发射 m:nary；∑、∫、∬ 仍保持原文。第四步原生 nary 发射实现后删除此兼容分支。Parser 的 Σ/∑ 识别规则保持一致。

连续补事件允许 A^cB^c（后续操作数大写）、A^{c}b（显式结束补事件参数）。A^cost 和 A^cfoo 有歧义，不能将 c 以后的文字静默丢到补事件之外。多字符上标应写 x^{2y}、x^{nn}；无括号的 x^12 可作为完整数字上标，但 x^2y 不允许。若 c 开头的内容是指数而非补事件，需要 generic 域和显式括号。

本模块没有普通正文的脱字符转义模式：包含 ^ 的输入即进入数学记号语法。独立 ^ 或“正文 ^ 提示”返回 MISSING_OPERAND error，“成本^收益”返回 INVALID_SCRIPT error；它们不会被视为无错误的普通文字。需要描述该字符时用“脱字符”文字。x^n 是合法数学表达式。这里明确现有语法边界，不新增 reporter 或质量门；未来接入质量门时必须保留上述诊断测试，不能假定所有正文中的 ^ 都可忽略。

Fail-fast 时整段输出可继续回落原文，但已经识别的 warnings 必须保留，随后追加首个 error；不实施错误恢复或部分树渲染。
