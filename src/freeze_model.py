import hashlib
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn

from baseline import calculate_metrics
from data import PROJECT_ROOT
from features import FEATURE_COLUMNS


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    models_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports"
    data_dir = PROJECT_ROOT / "data" / "processed"

    candidate_path = models_dir / "linear_candidate.joblib"
    final_path = models_dir / "forecast_pipeline.joblib"
    config_path = models_dir / "model_config.json"

    if final_path.exists() or config_path.exists():
        raise FileExistsError(
            "Model da duoc chot. Khong ghi de cau hinh."
        )

    pipeline = joblib.load(candidate_path)
    train = pd.read_csv(data_dir / "train.csv")
    validation = pd.read_csv(data_dir / "validation.csv")

    # Kiểm tra lại validation với quy tắc đầu ra đã chốt.
    raw_predictions = pipeline.predict(
        validation[FEATURE_COLUMNS]
    )
    predictions = np.maximum(raw_predictions, 0)
    metrics = calculate_metrics(validation["cnt"], predictions)

    with (reports_dir / "error_analysis_config.json").open(
        encoding="utf-8"
    ) as file:
        error_config = json.load(file)

    config = {
        "model_name": "LinearRegression",
        "model_version": "1.0",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_metric": "validation_MAE",
        "selection_note": "criterion_fixed_after_validation_before_test",
        "training_scope": "train_only_no_refit",
        "features": FEATURE_COLUMNS,
        "target": "cnt",
        "unit": "rentals_per_hour",
        "prediction_policy": "maximum(raw_prediction, 0)",
        "round_before_evaluation": False,
        "validation_metrics": metrics,
        "peak_hours": error_config["peak_hours"],
        "peak_requires_workingday": True,
        "bad_weather_codes": [3, 4],
        "train_start": str(train["timestamp"].min()),
        "train_end": str(train["timestamp"].max()),
        "validation_start": str(validation["timestamp"].min()),
        "validation_end": str(validation["timestamp"].max()),
        "test_start": "2012-09-01",
        "test_end": "2012-12-31",
        "sklearn_version": sklearn.__version__,
        "train_sha256": checksum(data_dir / "train.csv"),
        "validation_sha256": checksum(data_dir / "validation.csv"),
        "limitations": [
            "Underprediction during peak workingday hours",
            "Worse bad-weather validation MAE than baseline",
            "No weather-code-4 validation samples",
            "Historical dataset; current local use not validated",
        ],
    }

    # Lưu nguyên pipeline đã học, không gọi fit.
    joblib.dump(pipeline, final_path)
    config["pipeline_sha256"] = checksum(final_path)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)

    print("=== DA CHOT MODEL ===")
    print("Model: LinearRegression")
    print("Quy tac: du bao am duoc dua ve 0")
    print(f"Validation MAE: {metrics['MAE']:.4f}")
    print(f"Validation RMSE: {metrics['RMSE']:.4f}")
    print(f"Validation R2: {metrics['R2']:.4f}")
    print("Da luu models/forecast_pipeline.joblib")
    print("Da luu models/model_config.json")
    print("Chua doc hoac danh gia test.")


if __name__ == "__main__":
    main()