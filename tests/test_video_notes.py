import tempfile
import unittest
from pathlib import Path
from video_notes.storage import write
from video_notes.reviews import request, import_result, confirmed
from video_notes.domain import validate_document
from video_notes.pipeline import batch
from video_notes.locks import quota

class Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = {"workspace": str(self.root), "run_id": "test", "document": str(self.root / "doc.json"),
                    "topics": str(self.root / "topics.json")}
        write(self.run["document"], {"schema_version": 1, "blocks": [{"id": "b1", "type": "paragraph", "text": "这是审核前已经存在的正文证据"}]})
        write(self.run["topics"], {"topics": [{"id": "t1", "source_refs": ["source:1"]}]})

    def response(self, req):
        return {"schema_version": 1, "request_id": req["request_id"], "run_id": "test", "kind": "content",
                "reviewer": {"kind": "agent", "id": "author", "independence": "self_review"},
                "review_execution_id": "separate-review", "status": "confirmed", "findings": [], "input_hashes": req["inputs"],
                "topics": [{"topic_id": "t1", "block_ids": ["b1"], "evidence": "这是审核前已经存在的正文证据",
                            "review_note": "Compared against source", "source_refs": ["source:1"], "covered": True}]}

    def test_review_is_separate_and_stale_results_rejected(self):
        self.assertIsNone(confirmed(self.run, "content"))
        req = request(self.run, "content")
        path = self.root / "response.json"
        write(path, self.response(req))
        import_result(self.run, "content", path)
        self.assertEqual(confirmed(self.run, "content")["reviewer"]["independence"], "self_review")
        write(self.run["document"], {"schema_version": 1, "blocks": []})
        self.assertIsNone(confirmed(self.run, "content"))
        with self.assertRaises(ValueError):
            import_result(self.run, "content", path)

    def test_missing_topic_rejected(self):
        req = request(self.run, "content")
        response = self.response(req)
        response["topics"] = []
        path = self.root / "response.json"
        write(path, response)
        with self.assertRaises(ValueError):
            import_result(self.run, "content", path)

    def test_unknown_blocks_rejected(self):
        with self.assertRaises(ValueError):
            validate_document({"schema_version": 1, "blocks": [{"id": "x", "type": "mystery"}]})

    def test_quota_timeout_does_not_steal_lock(self):
        with quota(self.root / "locks", "word", timeout=0):
            with self.assertRaises(TimeoutError):
                with quota(self.root / "locks", "word", timeout=0):
                    pass
        self.assertEqual(list((self.root / "locks").iterdir()), [])

    def test_batch_path_collision_rejected(self):
        r = {"workspace": "same", "frames": "same", "lock_dir": "locks", "execution": {"download_cpu_slots": 2}}
        with self.assertRaises(ValueError):
            batch([r, r], "preflight")

if __name__ == "__main__":
    unittest.main()
