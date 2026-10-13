# Shared visual formula output contract

Both an Agent inspecting frames itself and a multimodal API caller use this
contract. Return ordinary JSON; provider-specific structured output is not required.

Each formulas[] entry must be an object, for example:

```json
{"type":"formula","format":"latex","text":"\\overline{A}\\cup B","placement":{"field":"concepts","index":0,"position":"after"}}
```

text contains one standalone mathematical expression in standard LaTeX, without
$, $$, \(...\), \[...\], Markdown or explanatory prose. Chinese explanations
belong in text/concepts/reasoning. Mixed text commands such as \text{} are deferred.
Escape backslashes correctly in JSON. Use explicit braces for script arguments.
Do not claim syntax validity proves mathematical correctness.

placement identifies a supplied content item: field is concepts, reasoning,
tables or text; index is zero-based (reasoning and text use index 0); position
is before or after. This is a proposed editorial anchor, not proof of video order.
Only provide an anchor when the formula's relationship to that content is clear.
Otherwise omit placement and describe uncertainty in prose; document generation
will require human placement rather than inventing it. Never collect all formulas
at the end of the document. Multiple formulas with the same anchor retain array order.

Shared notation and terminology:

- Probability event complement: \overline{A}; consecutive complements:
  \overline{A}\overline{B}. Do not transcribe an event complement as A^{c}.
- Union/intersection: \cup / \cap; distinguish them from arithmetic operators.
- Summation: \sum_{k=0}^{n} p_k; integral: \int_{0}^{1} f(x)\,dx;
  double integral: \iint_D f(x,y)\,dx\,dy. Preserve bounds and differential order.
- Functions: \sin, \cos, \log, \exp, not italic letter products.
- Fractions/radicals: \frac{a}{b}, \sqrt{x}; scripts: x^{n+1}, a_{ij}.
- Joint distribution F(x,y) and joint density f(x,y) are distinct. Preserve case,
  support regions, inequalities and conditions faithfully.

The host code attaches source frame identifiers, image hashes when available and
formula indices. Do not invent source hashes, validation results or certainty.
Frame ordering, editorial anchors and mathematical meaning require human review.
Existing string-array artifacts remain legacy; do not silently reinterpret them.
