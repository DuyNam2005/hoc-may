import hashlib
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from baseline import calculate_metrics, predict_baseline
from data import PROJECT_ROOT


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_results(result):
    table = pd.DataFrame([
        {"model": name, **metrics}
        for name, metrics in result["metrics"].items()
    ])
    print("\n=== KET QUA CUOI TREN TEST ===")
    print(table.to_string(index=False, float_format="%.4f"))

    print("\n=== SAI SO THEO NHOM TREN TEST ===")
    print(
        pd.DataFrame(result["group_metrics"]).to_string(
            index=False, float_format="%.2f"
        )
    )


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"
    models_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports"
    figures_dir = reports_dir / "figures"
    result_path = reports_dir / "test_metrics.json"

    # Chạy lại chỉ hiển thị kết quả đã lưu.
    if result_path.exists():
        with result_path.open(encoding="utf-8") as file:
            result = json.load(file)
        print("Dang hien thi ket qua test da luu.")
        print_results(result)
        return

    with (models_dir / "model_config.json").open(
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    pipeline_path = models_dir / "forecast_pipeline.joblib"

    # Kiểm tra mô hình và train không thay đổi sau khi chốt.
    if checksum(pipeline_path) != config["pipeline_sha256"]:
        raise ValueError("Pipeline da thay doi sau khi chot.")

    if checksum(data_dir / "train.csv") != config["train_sha256"]:
        raise ValueError("Train da thay doi sau khi chot.")

    if (
        checksum(data_dir / "validation.csv")
        != config["validation_sha256"]
    ):
        raise ValueError("Validation da thay doi sau khi chot.")

    if config["prediction_policy"] != "maximum(raw_prediction, 0)":
        raise ValueError("Quy tac dau ra khong khop.")

    pipeline = joblib.load(pipeline_path)
    train = pd.read_csv(data_dir / "train.csv")
    test_path = data_dir / "test.csv"
    test = pd.read_csv(test_path, parse_dates=["timestamp"])
    test = test.sort_values("timestamp").reset_index(drop=True)

    start = pd.Timestamp(config["test_start"])
    end_exclusive = pd.Timestamp(config["test_end"]) + pd.Timedelta(
        days=1
    )
    if test.empty or not (
        (test["timestamp"] >= start)
        & (test["timestamp"] < end_exclusive)
    ).all():
        raise ValueError("Khoang thoi gian test khong khop cau hinh.")

    actual = test["cnt"].to_numpy()
    raw_predictions = pipeline.predict(test[config["features"]])

    predictions = {
        "Baseline": np.maximum(
            predict_baseline(train, test[["weekday", "hr"]]),
            0,
        ),
        "LinearRegression": np.maximum(raw_predictions, 0),
    }

    peak_mask = (
        (test["workingday"] == 1)
        & test["hr"].isin(config["peak_hours"])
    ).to_numpy()

    groups = {
        "All": np.ones(len(test), dtype=bool),
        "Peak_workingday": peak_mask,
        "Other_hours": ~peak_mask,
        "Bad_weather": test["weathersit"].isin(
            config["bad_weather_codes"]
        ).to_numpy(),
    }
    for code in [1, 2, 3, 4]:
        groups[f"Weather_{code}"] = (
            test["weathersit"] == code
        ).to_numpy()

    overall_metrics = {}
    group_metrics = []

    prediction_table = test[
        ["timestamp", "hr", "workingday", "weathersit", "cnt"]
    ].copy()

    for name, predicted in predictions.items():
        overall_metrics[name] = calculate_metrics(actual, predicted)
        prediction_table[f"{name}_prediction"] = predicted

        for group_name, mask in groups.items():
            count = int(mask.sum())
            row = {
                "model": name,
                "group": group_name,
                "n": count,
                "MAE": None,
                "RMSE": None,
                "bias": None,
            }
            if count:
                errors = predicted[mask] - actual[mask]
                row.update({
                    "MAE": float(np.mean(np.abs(errors))),
                    "RMSE": float(np.sqrt(np.mean(errors ** 2))),
                    "bias": float(np.mean(errors)),
                })
            group_metrics.append(row)

    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    prediction_table.to_csv(
        reports_dir / "test_predictions.csv",
        index=False,
    )
    pd.DataFrame(group_metrics).to_csv(
        reports_dir / "test_error_groups.csv",
        index=False,
    )

    # Vẽ 7 ngày đầu test; giờ thiếu được để trống trên biểu đồ.
    first_hour = test["timestamp"].min()
    hours = pd.date_range(
        start=first_hour,
        periods=7 * 24,
        freq="h",
    )
    week = prediction_table.set_index("timestamp").reindex(hours)

    fig, axis = plt.subplots(figsize=(12, 4))
    axis.plot(week.index, week["cnt"], label="Actual")
    for name in predictions:
        axis.plot(
            week.index,
            week[f"{name}_prediction"],
            label=name,
            alpha=0.8,
        )

    axis.set_title("First 7 days of test - hourly rentals")
    axis.set_xlabel("Time")
    axis.set_ylabel("Rentals/hour")
    axis.grid(alpha=0.3)
    axis.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(figures_dir / "test_first_week.png", dpi=160)
    plt.close(fig)

    result = {
        "evaluation_split": "test",
        "model_version": config["model_version"],
        "training_scope": config["training_scope"],
        "prediction_policy": config["prediction_policy"],
        "test_rows": len(test),
        "test_start": str(test["timestamp"].min()),
        "test_end": str(test["timestamp"].max()),
        "test_sha256": checksum(test_path),
        "pipeline_sha256": config["pipeline_sha256"],
        "negative_raw_prediction_count": int(
            (raw_predictions < 0).sum()
        ),
        "metrics": overall_metrics,
        "group_metrics": group_metrics,
    }

    # Lưu kết quả tổng sau khi các đầu ra khác đã hoàn thành.
    with result_path.open("w", encoding="utf-8") as file:
        json.dump(
            result, file, indent=2,
            ensure_ascii=False, allow_nan=False,
        )

    print_results(result)
    print("\nDa luu ket qua test va bieu do trong reports/.")


if __name__ == "__main__":
    main()