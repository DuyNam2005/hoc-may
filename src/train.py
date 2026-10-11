import json

import joblib
import pandas as pd
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from baseline import calculate_metrics, predict_baseline
from data import PROJECT_ROOT
from features import FEATURE_COLUMNS, build_preprocessor


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"

    train = pd.read_csv(data_dir / "train.csv")
    validation = pd.read_csv(data_dir / "validation.csv")

    X_train = train[FEATURE_COLUMNS]
    y_train = train["cnt"]
    X_validation = validation[FEATURE_COLUMNS]
    y_validation = validation["cnt"]

    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", LinearRegression()),
        ]
    )

    # Encoder, scaler và mô hình đều chỉ học từ train.
    pipeline.fit(X_train, y_train)

    # Validation chỉ dùng để dự báo và đánh giá.
    predictions = pipeline.predict(X_validation)
    metrics = calculate_metrics(y_validation, predictions)

    baseline_predictions = predict_baseline(
        train,
        validation[["weekday", "hr"]],
    )
    baseline_metrics = calculate_metrics(
        y_validation,
        baseline_predictions,
    )

    comparison = pd.DataFrame(
        [
            {"Model": "Baseline", **baseline_metrics},
            {"Model": "LinearRegression", **metrics},
        ]
    )

    print("=== SO SANH TREN VALIDATION ===")
    print(comparison.to_string(index=False, float_format="%.4f"))
    print(f"\nSo du bao am: {(predictions < 0).sum()}")

    models_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports"
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Đây là mô hình ứng viên, chưa phải lựa chọn cuối.
    joblib.dump(
        pipeline,
        models_dir / "linear_candidate.joblib",
    )

    result = {
        "model": "LinearRegression",
        "status": "candidate",
        "evaluation_split": "validation",
        "features": FEATURE_COLUMNS,
        "sklearn_version": sklearn.__version__,
        "prediction_policy": "raw_unrounded",
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "negative_prediction_count": int((predictions < 0).sum()),
    }

    with (reports_dir / "linear_validation_metrics.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(result, file, indent=2, ensure_ascii=False)

    prediction_table = validation[["timestamp", "cnt"]].copy()
    prediction_table["baseline_prediction"] = baseline_predictions
    prediction_table["linear_prediction"] = predictions
    prediction_table.to_csv(
        reports_dir / "linear_validation_predictions.csv",
        index=False,
    )

    print("\nDa luu pipeline ung vien va ket qua validation.")


if __name__ == "__main__":
    main()