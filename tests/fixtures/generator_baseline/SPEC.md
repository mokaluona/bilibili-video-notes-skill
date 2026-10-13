# 生成端第一步 固定规格与现状基准

这些文件是测试输入与迁移验收材料，不是新的生成框架，也不修改公共流程规矩。

## 现状与目标分开

- `legacy_config.json` 覆盖全部旧 SECTIONS 类型、列表样式、摘要和两种图片编号。
- `expected_document_v1.json` 是独立编写的转换期望，覆盖逐块类型、ID、文本、样式标记和资产映射。v1 仅记录当前输出；未来 convert 改出 v2 时显式更新基准，不增加历史迁移义务。图片 caption 保留旧配置原文（自身带"图 6 "前缀），两个渲染器都会再叠一层编号，基准按现状整串断言，不视为期望格式。
- `style_contract.json` 分别记录模板及核心当前默认值。模板未显式设置表格整体对齐，单元格居中。第二步补表头后同步更新对应基准，表头不属于最终允许差异。`core_current.formula_font` 记的是正文字体，即核心公式未使用数学字体这条差异；`core_current.caption_prefix` 是格式串，`template.caption_prefix` 是字面前缀，两者不可直接比较。
- `current_parser_snapshot.json` 保存当前解析树及 strict 错误，包含已知缺陷。每条另有 `current_state`：`correct`（现状即目标）、`detected`（现状已拒绝）、`silently_wrong`（**无报错但输出错误**：空上下标、`x^2y` 上标吞掉 `y`、`A^cost` 渲染成补集加 ost）、`unsupported`（尚无原生支持）。四类必须分开验收：第二步若只补 nary，会漏掉 `silently_wrong` 四项。它的断言是现状保护，不代表缺陷被认可；第二步应将相关快照测试替换为 ParseResult 通知断言。
- `formula_cases.json` 是未来目标规格。第一步只检查语料完整性，尚未对新解析器或新发射器验收。`Σ`（U+03A3）现在能解析、`∑`（U+2211）整串回退，是顶层算子表要消除的不对称，不是两个无关用例。
- `notice_locations.json` 固定块、表格行列、列表条目与 text_span 的坐标例子。`block_ids_are_illustrative` 为真，`real_block_ids` 给出它们在基准文档中的真实 ID。
- `provenance.json` 记录第三讲实际配置及临时脚本指纹、真实节选位置与合成素材范围。不含本机路径、cookie 或源视频标识（BV 号）；`source_ref` 是不可反查的代号，`source_identifier_recorded` 为 false 表示这是刻意的。`legacy_real_sections.fixture_index` 是 `SECTIONS` 的 0 基下标，`source_section_index` 是原配置中的位置。

## 公式规格

算子识别和发射共用顶层词法表：Σ/∑ 对应 U+2211 和 undOvr，∫/∬ 分别对应 U+222B/U+222C 和 subSup。domain 后缀规则与此分离。

新写法使用 `∫_{x}^{2}{x e^{-y}} dy`。解析器在算子处读取上下限，再吸收紧邻的花括号主体；主体必须进入 m:e，微分符号在其外。嵌套积分绑定各自的主体。隐式被积式1要求写 `{1}`，不根据 dy 猜测边界。

节点缺少下限或上限时分别设置 subHide/supHide；裸算子有显式主体但没有上下限。上下限符号必须可见，字体参数可传，不能丢失颜色和字号。

临时 rich_math 注入器的可取规格是 nary 字符、limLoc、上下限样式；其 m:e 只有零宽占位符、主体留在兄弟节点、缺少 subHide 等行为不继承。不能把补字符集当成原生 nary 实现。

## 诊断契约

parse 恒定返回 ParseResult(nodes, notices)，删除 strict 通道。预期错误不抛 ValueError；调用方汇总诊断后执行质量门。错误码在语料中列出，未闭合、空参数、缺操作数、歧义及其他回退分别可识别。

第二步对合法但尚不支持发射的算子记录 UNSUPPORTED_NARY warning；旧无主体边界写法记录 LEGACY_NARY_BODY warning，目标生产基准最终清零。格式畸形始终 blocking，不能按是否出现算子符号宽泛放行。

定位为 block_id + sub_path + text_span，即 `{code, severity, block_id, sub_path, text_span, message}`；语料中的 `code` 字段与 `notice_locations.json` 用同一套命名，第二步落 `ParseResult.notices` 时不要另起字段名。

`sub_path` 的行号是**渲染行序号**：表格表头为 row 0，因此 `block['rows'][i]` 对应 row=i+1；列表用 0 基 `item`；`col` 为 0 基列号。`text` 是**该坐标处各 run 合并后**的文本，也就是交给 `add_text` 的那个字符串；单元格和列表条目在模型里都是 run 数组，不先合并就取不到稳定偏移。`text_span` 是相对该文本的 Unicode 字符左闭右开偏移，与字幕/截图 source_refs 无关。

按第二步实施中的补充要求，结构报告落盘和模板预检推迟到第四步。本步仅返回 Notice，不新增交付质量门。第四步模板变薄前由核心承接报告生产，第五步接入 continuation 与 quality；届时报告缺失、未运行或构建失配均 blocking。结构错误不得改写字幕覆盖分数。

## 后续验收

第二步将现状快照改为 code/severity/text_span 断言，并按 `current_state` 分批：先 `unsupported`（补 nary），再 `silently_wrong` 四项（这四个是当前已经在产出错误结果，不是缺功能），最后 `detected` 六项转 blocking。第四步对 formula_cases 的期望执行真实 OMML 检查，检查 m:naryPr、chr、limLoc、隐藏状态以及 m:e 的主体。再实际渲染求和、积分、嵌套、复杂上下标和跨页表格；当前第一步没有宣称视觉兼容或未来公式能力通过。

临时脚本继续保留，直到有效能力被固定用例与核心实现接替。AGENTS.md、README.md、生产入口、schema 与解析行为在本步均不改动。

## 第二步实现状态

现状快照保留为历史材料，运行时不再对拍错误解析树。test_formula_diagnostics 对23项语料及独立错误类别执行新规格断言。原生 nary 发射、Renderer 迁移、schema 升级和结构报告接线均未实施。重复表头修复已从 Parser 阶段撤出，其基准恢复未修复状态；后续独立验收和提交。
