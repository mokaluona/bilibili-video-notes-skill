# 公式输入与扩展约定

正文、表头、单元格和公式块共用 `add_text`。默认领域为 mathematics。

| 输入 | 输出 |
|---|---|
| A^c、A^{c}、A^C | A 的补事件上横线 |
| (AB)^c、[A(B^c∪C)D]^c | 整体或嵌套上横线 |
| A_i、A_{ij} | 原生下标 |
| x^2、x^{n+1}、p^(n−k) | 原生上标 |

孤立下划线、填空线及无法解析的文字默认原样保留；`strict=True` 报错并带原句。
当前回落以整个输入片段为单位，因此混有错误写法的片段需要作者拆分或修正，
才能排版其中的合法公式。验证器仍拦截正文中残留的大小写补事件记号。
这里不是完整 LaTeX 引擎；复杂结构需新增节点及渲染支持。

`name` 控制普通文字字体；原生数学结构固定使用 Cambria Math。
若 c 是指数而非补事件，调用 `add_text(..., domain='generic')`。
模板默认使用数学规则，其他学科需显式选领域，不从正文猜测。

注册规则 `register_domain(name, rule)`，rule(operator, argument) 返回
`(node_kind, consumed_characters)` 或 None。无括号写法按声明长度消费，
花括号写法必须完整匹配。旧的字符串返回值表示消费完整参数，仅作兼容。
例如补事件规则对以 c 开头的参数返回 ('bar', 1)，使 A^cB^c 分别取非。
新学科复用 model 与 word 层；新增结构必须同时实现输出与回归测试。

回归测试：`python -m unittest discover -s tests`。
旧命令 `python scripts/test_formula_layout.py` 转发到同一组测试。
