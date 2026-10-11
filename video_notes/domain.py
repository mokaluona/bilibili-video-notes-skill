"""Pure contract validation; no filesystem or process access."""
BLOCKS = {"heading", "paragraph", "list", "table", "image", "formula", "explanation", "tip"}
KINDS = {"vision", "content", "page", "sample_page"}

def validate_document(doc):
    if doc.get("schema_version") != 1:
        raise ValueError("Unsupported document schema")
    ids = set()
    for block in doc["blocks"]:
        if block["id"] in ids or block["type"] not in BLOCKS:
            raise ValueError("Duplicate block ID or unknown block type")
        ids.add(block["id"])
        if block["type"] == "formula" and block.get("format", "plain") != "plain":
            raise ValueError("Only plain formulas currently supported")
        kind = block["type"]
        if kind in {"heading", "paragraph", "formula", "explanation", "tip"} and not isinstance(block.get("text"), str):
            raise ValueError("Text block requires a string")
        if kind == "heading" and block.get("level", 1) not in (1, 2, 3):
            raise ValueError("Heading level must be 1 to 3")
        if kind == "list" and not isinstance(block.get("items"), list):
            raise ValueError("List requires items")
        if kind == "table":
            if not block.get("headers") or any(len(row) != len(block["headers"]) for row in block["rows"]):
                raise ValueError("Invalid table dimensions")
        if kind == "image" and (not block.get("asset_id") or not isinstance(block.get("caption"), str)):
            raise ValueError("Image requires asset ID and caption")
    return doc

def validate_identity(reviewer):
    if reviewer.get("kind") not in {"human", "agent"} or not reviewer.get("id"):
        raise ValueError("Reviewer kind and ID required")
    if reviewer.get("independence") not in {"self_review", "independent", "unknown"}:
        raise ValueError("Review independence must be explicit")
    if reviewer['kind'] == 'agent' and reviewer['independence'] == 'independent':
        raise ValueError('Independent agent review provenance is not supported; use self_review or unknown')
