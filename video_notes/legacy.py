"""Read-only SECTIONS migration; new content never writes the old format."""
from .domain import validate_document

def convert(config):
    blocks, assets = [], {}
    for i, item in enumerate(config["SECTIONS"]):
        kind = item[0]
        block = {"id": f"legacy-{i+1}"}
        if kind in ("h1", "h2", "h3"):
            block.update(type="heading", text=item[1], level=int(kind[1]))
        elif kind in ("body", "bold", "red", "why", "tips", "formula"):
            block.update(type={"why": "explanation", "tips": "tip", "formula": "formula"}.get(kind, "paragraph"), text=item[1])
            if kind in ("bold", "red"):
                block["bold"] = True
            if kind == "red":
                block["red"] = True
        elif kind == "bullet":
            block.update(type="list", items=[[{"text": x[0], "bold": x[1], "red": x[2]}] for x in item[1]])
        elif kind == "table":
            block.update(type="table", headers=item[1], rows=item[2])
        elif kind == "img":
            name = str(item[1])
            if not name.endswith('.jpg'):
                name = (name if name.startswith('frame_') else 'frame_' + name) + '.jpg'
            asset_id = f"image-{i+1}"
            assets[asset_id] = name
            block.update(type="image", asset_id=asset_id, caption=item[2])
        else:
            raise ValueError(f"Unknown legacy kind: {kind}")
        blocks.append(block)
    # Summary is explicit and emitted only when supplied by old content.
    if config.get("SUMMARY"):
        blocks.extend([{"id": "legacy-summary-heading", "type": "heading", "text": "本节要点总结", "level": 1},
                       {"id": "legacy-summary", "type": "list", "items": config["SUMMARY"]}])
    return validate_document({"schema_version": 1, "metadata": {"title": config["TITLE"], "source": config.get("SOURCE", "")},
                              "blocks": blocks, "assets": assets})
