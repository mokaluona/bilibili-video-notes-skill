from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

def properties(size, bold, red):
    rp = OxmlElement('w:rPr')
    fonts = OxmlElement('w:rFonts')
    for key in ('ascii', 'hAnsi'): fonts.set(qn('w:' + key), 'Cambria Math')
    fonts.set(qn('w:eastAsia'), '宋体'); rp.append(fonts)
    for tag, value in [('sz', str(round(size * 2))), ('color', 'C00000' if red else '000000')]:
        el = OxmlElement('w:' + tag); el.set(qn('w:val'), value); rp.append(el)
    if bold: rp.append(OxmlElement('w:b'))
    return rp

def emit(parent, node, size, bold, red):
    if node.kind in ('sequence', 'group'):
        if node.kind == 'group': emit(parent, type(node)('text', node.text[0]), size, bold, red)
        for i, child in enumerate(node.children):
            emit(parent, child, size, bold, red)
            if child.kind == 'bar' and i + 1 < len(node.children) and node.children[i+1].kind == 'bar':
                emit(parent, type(node)('text', ' '), size, bold, red)
        if node.kind == 'group': emit(parent, type(node)('text', node.text[1]), size, bold, red)
    elif node.kind == 'text':
        run = OxmlElement('m:r'); run.append(properties(size, bold, red))
        t = OxmlElement('m:t'); t.set(qn('xml:space'), 'preserve'); t.text = node.text; run.append(t); parent.append(run)
    elif node.kind == 'bar':
        el = OxmlElement('m:bar'); pr = OxmlElement('m:barPr'); pos = OxmlElement('m:pos'); pos.set(qn('m:val'), 'top'); pr.append(pos); el.append(pr)
        e = OxmlElement('m:e'); emit(e, node.children[0], size, bold, red); el.append(e); parent.append(el)
    elif node.kind in ('sub', 'sup'):
        el = OxmlElement('m:sSub' if node.kind == 'sub' else 'm:sSup')
        for tag, child in zip(('e', node.kind), node.children):
            slot = OxmlElement('m:' + tag); emit(slot, child, size, bold, red); el.append(slot)
        parent.append(el)
    else: raise ValueError('Unsupported expression node: ' + node.kind)

def plain(node):
    if node.kind == 'text': return node.text
    if node.kind == 'group':
        parts = [plain(n) for n in node.children]
        if all(p is not None for p in parts): return node.text[0] + ''.join(parts) + node.text[1]
    return None

def append_nodes(paragraph, nodes, name, size, bold, red):
    for i, node in enumerate(nodes):
        text = plain(node)
        if text is not None:
            run = paragraph.add_run(text); run.font.name = name
            run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), name)
            run.font.size = Pt(size); run.bold = bold
            if red: run.font.color.rgb = RGBColor(192, 0, 0)
        else:
            math = OxmlElement('m:oMath'); emit(math, node, size, bold, red); paragraph._p.append(math)
        if node.kind == 'bar' and i + 1 < len(nodes) and nodes[i+1].kind == 'bar': paragraph.add_run(' ')
