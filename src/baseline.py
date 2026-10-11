import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from data import PROJECT_ROOT


def predict_baseline(train, inputs):
    # Chỉ tính các giá trị trung bình từ train.
    mean_by_weekday_hour = train.groupby(
        ["weekday", "hr"]
    )["cnt"].mean()

    mean_by_hour = train.groupby("hr")["cnt"].mean()
    global_mean = train["cnt"].mean()

    keys = pd.MultiIndex.from_frame(inputs[["weekday", "hr"]])
    predictions = mean_by_weekday_hour.reindex(keys).to_numpy()

    # Nếu không có nhóm thứ/giờ trong train:
    # dùng trung bình theo giờ, rồi trung bình toàn train.
    fallback = inputs["hr"].map(mean_by_hour).fillna(global_mean)
    predictions = np.where(
        np.isnan(predictions),
        fallback.to_numpy(),
        predictions,
    )

    return predictions


def calculate_metrics(actual, predicted):
    return {
        "MAE": float(mean_absolute_error(actual, predicted)),
        "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        "R2": float(r2_score(actual, predicted)),
    }


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"

    train = pd.read_csv(data_dir / "train.csv")
    validation = pd.read_csv(data_dir / "validation.csv")

    # Hàm dự báo chỉ nhận các biến lịch của validation.
    predictions = predict_baseline(
        train,
        validation[["weekday", "hr"]],
    )
    metrics = calculate_metrics(validation["cnt"], predictions)

    print("=== BASELINE TREN VALIDATION ===")
    print(f"MAE:  {metrics['MAE']:.2f} luot/gio")
    print(f"RMSE: {metrics['RMSE']:.2f} luot/gio")
    print(f"R2:   {metrics['R2']:.4f}")

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "model": "mean_by_weekday_hour",
        "evaluation_split": "validation",
        "metrics": metrics,
        "fallback": "hour_mean_then_global_mean_from_train",
    }

    with (reports_dir / "baseline_validation_metrics.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(result, file, indent=2, ensure_ascii=False)

    comparison = validation[["timestamp", "cnt"]].copy()
    comparison["baseline_prediction"] = predictions
    comparison.to_csv(
        reports_dir / "baseline_validation_predictions.csv",
        index=False,
    )

    print("\nDa luu ket qua baseline vao reports/")


if __name__ == "__main__":
    main()