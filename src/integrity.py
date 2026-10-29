"""Stable fingerprints for CSV data and exact fingerprints for binary models."""

import hashlib
import json
import math
from pathlib import Path


def checksum(path):
    path = Path(path)
    content = path.read_bytes()
    if path.suffix.lower() == ".csv":
        # Match the CRLF fingerprints in the original model configuration.
        # Only line endings change; every other byte remains significant.
        content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return hashlib.sha256(content).hexdigest()


def verify_frozen_artifacts(root, config):
    root = Path(root)
    artifacts = {
        "pipeline_sha256": root / "models/forecast_pipeline.joblib",
        "train_sha256": root / "data/processed/train.csv",
        "validation_sha256": root / "data/processed/validation.csv",
    }
    for key, path in artifacts.items():
        if checksum(path) != config.get(key):
            raise ValueError(f"Artifact khong khop cau hinh: {path.name}.")
    if config.get("prediction_policy") != "maximum(raw_prediction, 0)":
        raise ValueError("Quy tac dau ra khong khop.")


def _reject_constant(value):
    raise ValueError(f"JSON contains a non-finite number: {value}")


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number exceeds the finite float range.")
    return number


def read_verified_test_report(root, config):
    """Shared by the command-line evaluator and the web evaluation endpoint."""
    root = Path(root)
    verify_frozen_artifacts(root, config)
    with (root / "reports/test_metrics.json").open(encoding="utf-8") as file:
        result = json.load(
            file, parse_constant=_reject_constant, parse_float=_finite_json_float
        )
    if not isinstance(result, dict):
        raise ValueError("Bao cao test phai la JSON object.")
    for key in (
        "pipeline_sha256", "model_version", "training_scope", "prediction_policy",
    ):
        if key not in config or result.get(key) != config[key]:
            raise ValueError(f"Bao cao test khong khop cau hinh: {key}.")
    if result.get("evaluation_split") != "test":
        raise ValueError("Bao cao khong phai ket qua test.")
    if checksum(root / "data/processed/test.csv") != result.get("test_sha256"):
        raise ValueError("Test da thay doi so voi bao cao da luu.")

    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("Bao cao thieu metric tong the.")
    for model in ("Baseline", "LinearRegression"):
        row = metrics.get(model)
        if not isinstance(row, dict) or not all(
            finite(row.get(key)) for key in ("MAE", "RMSE", "R2")
        ):
            raise ValueError(f"Metric khong hop le: {model}.")
        if row["MAE"] < 0 or row["RMSE"] < 0:
            raise ValueError("Sai so khong duoc am.")
    groups = result.get("group_metrics")
    if not isinstance(groups, list) or not groups:
        raise ValueError("Bao cao thieu metric theo nhom.")
    for row in groups:
        if (
            not isinstance(row, dict)
            or row.get("model") not in metrics
            or not isinstance(row.get("group"), str)
            or type(row.get("n")) is not int or row["n"] < 0
        ):
            raise ValueError("Nhom danh gia khong hop le.")
        values = [row.get(key) for key in ("MAE", "RMSE", "bias")]
        if row["n"] == 0:
            if any(value is not None for value in values):
                raise ValueError("Nhom khong co mau phai co metric null.")
        elif not all(finite(value) for value in values):
            raise ValueError("Metric nhom khong hop le.")
    return result
