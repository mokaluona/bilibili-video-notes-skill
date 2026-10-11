"""Requests freeze evidence; imports never modify authored content."""
import uuid
from pathlib import Path
from .storage import read, write, digest, now
from .domain import KINDS, validate_document, validate_identity

def inputs(run, kind):
    if kind == "vision":
        paths = [Path(run["workspace"]) / "candidates.json"]
        candidates = read(paths[0])
        root = Path(run["frames"]).resolve()
        for item in candidates:
            image = (root / item["path"]).resolve()
            if not image.is_relative_to(root):
                raise ValueError("Frame path escapes frame root")
            paths.append(image)
    elif kind == "content":
        paths = [Path(run["document"]), Path(run["topics"])]
    else:
        from .rendering import current_render
        current_render(run, kind == 'sample_page')
        paths = [Path(run["workspace"]) / ('sample-render.json' if kind == 'sample_page' else 'final-render.json')]
        artifact = read(paths[0])
        paths += [Path(x) for x in artifact["page_images"]]
        paths += [Path(artifact["document_path"])]
    if run.get("subtitle"):
        paths.append(Path(run["subtitle"]))
    return [{"path": str(p.resolve()), "sha256": digest(p)} for p in paths]

def request(run, kind):
    if kind not in KINDS:
        raise ValueError("Unknown review kind")
    if kind == "content":
        validate_document(read(run["document"]))
    folder = Path(run["workspace"]) / "reviews"
    old = read(folder / f"{kind}-request.json") if (folder / f"{kind}-request.json").exists() else None
    req = {"schema_version": 1, "run_id": run["run_id"], "request_id": str(uuid.uuid4()),
           "kind": kind, "created_at": now(), "inputs": inputs(run, kind),
           "expected_result_schema": "review-response-v1", "round": old["round"] + 1 if old else 1,
           "previous_request": old["request_id"] if old else None}
    write(folder / f"{kind}-request.json", req)
    return req

def validate_response(run, req, result):
    if result.get("schema_version") != 1 or result.get("request_id") != req["request_id"]:
        raise ValueError("Wrong review request or schema")
    if result.get("kind") != req["kind"] or result.get("run_id") != run["run_id"]:
        raise ValueError("Wrong review kind or run")
    validate_identity(result["reviewer"])
    if not result.get("review_execution_id") or not result.get("findings") == []:
        raise ValueError("Execution ID required and unresolved findings block confirmation")
    if result.get("status") != "confirmed" or result.get("input_hashes") != req["inputs"]:
        raise ValueError("Only confirmed, version-bound results accepted")
    if inputs(run, req["kind"]) != req["inputs"]:
        raise ValueError("Review inputs changed; create a new request")
    if req["kind"] == "content":
        doc = read(run["document"])
        blocks = {b["id"]: b for b in doc["blocks"]}
        topics = read(run["topics"])["topics"]
        expected = {x["id"] for x in topics}
        if len(expected) != len(topics):
            raise ValueError("Duplicate source topic IDs")
        source_refs = {x["id"]: x["source_refs"] for x in topics}
        items = result["topics"]
        if len(items) != len(expected) or {x["topic_id"] for x in items} != expected:
            raise ValueError("Every source topic needs exactly one review")
        for item in items:
            if item.get("covered") is not True or not item.get("review_note") or not item.get("source_refs"):
                raise ValueError("Coverage review incomplete")
            if item["source_refs"] != source_refs[item["topic_id"]]:
                raise ValueError("Review source references differ from source inventory")
            texts = [blocks[x].get("text", "") for x in item["block_ids"]]
            if len(item.get("evidence", "").strip()) < 8 or not any(item["evidence"] in t for t in texts):
                raise ValueError("Evidence must quote an existing block")
    elif req["kind"] in ("page", "sample_page"):
        artifact = Path(run["workspace"]) / ('sample-render.json' if req['kind'] == 'sample_page' else 'final-render.json')
        count = read(artifact)["pages"]
        if set(result["pages_reviewed"]) != set(range(1, count + 1)):
            raise ValueError("Every final page needs review")
    else:
        selected = read(Path(run["workspace"]) / "candidates.json")
        expected = {x["frame_id"] for x in selected}
        image_hashes = {x["frame_id"]: digest(Path(run["frames"]) / x["path"]) for x in selected}
        records = result["records"]
        if len(records) != len(expected) or {x["frame_id"] for x in records} != expected:
            raise ValueError("Every selected frame needs a visual record")
        for record in records:
            if record.get("sha256") != image_hashes[record["frame_id"]]:
                raise ValueError("Visual record hash differs from reviewed image")
            if record.get("error") is not None or record.get("complete") is not True:
                raise ValueError("Unresolved visual extraction")
    return result

def import_result(run, kind, path):
    folder = Path(run["workspace"]) / "reviews"
    req = read(folder / f"{kind}-request.json")
    result = validate_response(run, req, read(path))
    write(folder / f"{kind}-result.json", result)
    return result

def confirmed(run, kind):
    folder = Path(run["workspace"]) / "reviews"
    try:
        return validate_response(run, read(folder / f"{kind}-request.json"), read(folder / f"{kind}-result.json"))
    except (OSError, ValueError, KeyError):
        return None
