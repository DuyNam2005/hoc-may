import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluate
from integrity import checksum


class TestChecksums(unittest.TestCase):
    def test_csv_line_endings_are_equivalent_but_values_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            original = b"hr,cnt\r\n1,20\r\n"
            path.write_bytes(original)
            expected = hashlib.sha256(original).hexdigest()
            self.assertEqual(checksum(path), expected)
            path.write_bytes(original.replace(b"\r\n", b"\n"))
            self.assertEqual(checksum(path), expected)
            path.write_bytes(b"hr,cnt\n1,21\n")
            self.assertNotEqual(checksum(path), expected)

    def test_model_checksum_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.joblib"
            path.write_bytes(b"binary\r\ncontent")
            before = checksum(path)
            path.write_bytes(b"binary\ncontent")
            self.assertNotEqual(checksum(path), before)


class TestCachedEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = {}
        for relative, content in {
            "models/forecast_pipeline.joblib": b"frozen-model",
            "data/processed/train.csv": b"hr,cnt\r\n1,20\r\n",
            "data/processed/validation.csv": b"hr,cnt\r\n2,30\r\n",
            "data/processed/test.csv": b"hr,cnt\r\n3,40\r\n",
        }.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            self.original[path] = content
        config = {
            "pipeline_sha256": checksum(self.root / "models/forecast_pipeline.joblib"),
            "train_sha256": checksum(self.root / "data/processed/train.csv"),
            "validation_sha256": checksum(self.root / "data/processed/validation.csv"),
            "prediction_policy": "maximum(raw_prediction, 0)",
            "model_version": "1.0",
            "training_scope": "train_only_no_refit",
        }
        (self.root / "models/model_config.json").write_text(json.dumps(config))
        self.result = {
            **{key: config[key] for key in (
                "pipeline_sha256", "model_version", "training_scope", "prediction_policy"
            )},
            "evaluation_split": "test",
            "test_sha256": checksum(self.root / "data/processed/test.csv"),
            "metrics": {
                model: {"MAE": 1.0, "RMSE": 2.0, "R2": 0.5}
                for model in ("Baseline", "LinearRegression")
            },
            "group_metrics": [{
                "model": "LinearRegression", "group": "All", "n": 1,
                "MAE": 1.0, "RMSE": 2.0, "bias": -1.0,
            }],
        }
        self.report = self.root / "reports/test_metrics.json"
        self.report.parent.mkdir()
        self.save_report()
        self.addCleanup(patch.stopall)
        patch.object(evaluate, "PROJECT_ROOT", self.root).start()
        self.display = patch.object(evaluate, "print_results").start()
        self.load = patch.object(
            evaluate.joblib, "load", side_effect=AssertionError("Must not rerun inference")
        ).start()

    def save_report(self):
        self.report.write_text(json.dumps(self.result))

    def test_valid_cache_displays_without_rerunning_inference(self):
        evaluate.main()
        self.display.assert_called_once_with(self.result)
        self.load.assert_not_called()

    def test_changed_model_or_data_rejects_cached_report(self):
        for path, content in self.original.items():
            with self.subTest(path=path.name):
                path.write_bytes(content + b"changed")
                try:
                    with self.assertRaises(ValueError):
                        evaluate.main()
                finally:
                    path.write_bytes(content)
        self.display.assert_not_called()

    def test_cache_metadata_must_match_configuration(self):
        for key in (
            "pipeline_sha256", "model_version", "training_scope",
            "prediction_policy", "evaluation_split", "test_sha256",
        ):
            original = self.result[key]
            with self.subTest(key=key):
                self.result[key] = "wrong"
                self.save_report()
                with self.assertRaises(ValueError):
                    evaluate.main()
                self.result[key] = original
        self.display.assert_not_called()

    def test_lf_checkout_can_use_original_crlf_report(self):
        for path, content in self.original.items():
            if path.suffix == ".csv":
                path.write_bytes(content.replace(b"\r\n", b"\n"))
        evaluate.main()
        self.display.assert_called_once()

    def test_corrupt_or_incomplete_report_is_not_displayed(self):
        for content in (
            "{broken", "[]", "{}",
            json.dumps({**self.result, "metrics": {}}),
            json.dumps({**self.result, "group_metrics": []}),
            json.dumps(self.result).replace('"MAE": 1.0', '"MAE": 1e999'),
        ):
            with self.subTest(content=content[:60]):
                self.report.write_text(content)
                with self.assertRaises(ValueError):
                    evaluate.main()
        self.display.assert_not_called()

    def test_web_uses_same_report_verification(self):
        from backend import main as server
        from fastapi import HTTPException
        config = json.loads((self.root / "models/model_config.json").read_text())
        with patch.object(server, "PROJECT_ROOT", self.root), patch.object(
            server.app.state, "model_config", config, create=True
        ):
            self.assertEqual(server.evaluation(), self.result)
            for key in ("pipeline_sha256", "model_version", "prediction_policy"):
                with self.subTest(key=key):
                    self.report.write_text(json.dumps({**self.result, key: "stale"}))
                    with self.assertRaises(HTTPException) as caught:
                        server.evaluation()
                    self.assertEqual(caught.exception.status_code, 503)
            for content in ("{broken", "{}", "[]"):
                with self.subTest(content=content):
                    self.report.write_text(content)
                    with self.assertRaises(HTTPException) as caught:
                        server.evaluation()
                    self.assertEqual(caught.exception.status_code, 503)
            self.report.unlink()
            with self.assertRaises(HTTPException) as caught:
                server.evaluation()
            self.assertEqual(caught.exception.status_code, 503)

    def test_web_rejects_changed_test_data_and_recovers(self):
        from backend import main as server
        from fastapi import HTTPException
        config = json.loads((self.root / "models/model_config.json").read_text())
        path = self.root / "data/processed/test.csv"
        with patch.object(server, "PROJECT_ROOT", self.root), patch.object(
            server.app.state, "model_config", config, create=True
        ):
            path.write_bytes(b"hr,cnt\n3,999\n")
            with self.assertRaises(HTTPException) as caught:
                server.evaluation()
            self.assertEqual(caught.exception.status_code, 503)
            path.write_bytes(self.original[path])
            self.assertEqual(server.evaluation(), self.result)


if __name__ == "__main__":
    unittest.main()
