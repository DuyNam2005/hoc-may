import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from baseline import calculate_metrics, predict_baseline
from data import PROJECT_ROOT
from features import FEATURE_COLUMNS


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"
    reports_dir = PROJECT_ROOT / "reports"
    figures_dir = reports_dir / "figures"
    models_dir = PROJECT_ROOT / "models"
    figures_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(data_dir / "train.csv")
    validation = pd.read_csv(data_dir / "validation.csv")

    # Chốt giờ cao điểm từ train, không chọn bằng validation/test.
    hourly_mean = (
        train[train["workingday"] == 1]
        .groupby("hr")["cnt"]
        .mean()
        .sort_values(ascending=False, kind="stable")
    )
    peak_hours = sorted(int(hour) for hour in hourly_mean.head(4).index)

    print(f"Gio cao diem ngay lam viec, chon tu train: {peak_hours}")

    config = {
        "peak_hours": peak_hours,
        "peak_requires_workingday": True,
        "peak_selection": "top_4_hourly_means_on_training_workingdays",
        "bad_weather_codes": [3, 4],
        "evaluation_split": "validation",
    }
    with (reports_dir / "error_analysis_config.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(config, file, indent=2)

    linear = joblib.load(models_dir / "linear_candidate.joblib")
    sgd = joblib.load(models_dir / "sgd_candidate_0.001.joblib")

    predictions = {
        "Baseline": predict_baseline(
            train, validation[["weekday", "hr"]]
        ),
        "LinearRegression": linear.predict(
            validation[FEATURE_COLUMNS]
        ),
        "SGD_0.001": sgd.predict(validation[FEATURE_COLUMNS]),
    }

    peak_mask = (
        (validation["workingday"] == 1)
        & validation["hr"].isin(peak_hours)
    )
    bad_weather_mask = validation["weathersit"].isin([3, 4])

    groups = {
        "All": np.ones(len(validation), dtype=bool),
        "Peak_workingday": peak_mask.to_numpy(),
        "Other_hours": (~peak_mask).to_numpy(),
        "Bad_weather": bad_weather_mask.to_numpy(),
        "Weather_1": (validation["weathersit"] == 1).to_numpy(),
        "Weather_2": (validation["weathersit"] == 2).to_numpy(),
        "Weather_3": (validation["weathersit"] == 3).to_numpy(),
        "Weather_4": (validation["weathersit"] == 4).to_numpy(),
    }

    actual = validation["cnt"].to_numpy()
    rows = []
    hourly_errors = {}

    prediction_table = validation[
        ["timestamp", "hr", "workingday", "weathersit", "cnt"]
    ].copy()

    for model_name, predicted in predictions.items():
        predicted = np.asarray(predicted)
        prediction_table[f"{model_name}_prediction"] = predicted

        absolute_error = np.abs(actual - predicted)
        hourly_errors[model_name] = (
            pd.DataFrame({
                "hr": validation["hr"].to_numpy(),
                "absolute_error": absolute_error,
            })
            .groupby("hr")["absolute_error"]
            .mean()
        )

        for group_name, mask in groups.items():
            count = int(mask.sum())
            row = {
                "model": model_name,
                "group": group_name,
                "n": count,
            }

            if count == 0:
                row.update({
                    "MAE": np.nan,
                    "RMSE": np.nan,
                    "bias": np.nan,
                })
            else:
                metrics = calculate_metrics(
                    actual[mask], predicted[mask]
                )
                row.update({
                    "MAE": metrics["MAE"],
                    "RMSE": metrics["RMSE"],
                    "bias": float(
                        np.mean(predicted[mask] - actual[mask])
                    ),
                })

            rows.append(row)

    results = pd.DataFrame(rows)
    print("\n=== SAI SO THEO NHOM TREN VALIDATION ===")
    print(results.to_string(index=False, float_format="%.2f"))

    results.to_csv(
        reports_dir / "validation_error_groups.csv",
        index=False,
    )
    prediction_table.to_csv(
        reports_dir / "validation_error_predictions.csv",
        index=False,
    )

    # Sai số theo từng giờ, tính trên tất cả ngày của validation.
    fig, axis = plt.subplots(figsize=(10, 4))
    for model_name, errors in hourly_errors.items():
        axis.plot(
            errors.index,
            errors.values,
            marker="o",
            label=model_name,
        )

    axis.set_title("Validation MAE by hour - all days")
    axis.set_xlabel("Hour")
    axis.set_ylabel("MAE (rentals/hour)")
    axis.set_xticks(range(24))
    axis.grid(alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "validation_mae_by_hour.png", dpi=160)
    plt.close(fig)

    # Chỉ vẽ nhóm thời tiết thực sự có dữ liệu.
    weather_rows = results[
        results["group"].isin([
            "Weather_1", "Weather_2", "Weather_3", "Weather_4"
        ])
        & (results["n"] > 0)
    ]
    weather_table = weather_rows.pivot(
        index="group",
        columns="model",
        values="MAE",
    )

    axis = weather_table.plot.bar(figsize=(9, 4), rot=0)
    axis.set_title("Validation MAE by weather")
    axis.set_xlabel("Weather code")
    axis.set_ylabel("MAE (rentals/hour)")
    axis.grid(axis="y", alpha=0.3)
    fig = axis.get_figure()
    fig.tight_layout()
    fig.savefig(figures_dir / "validation_mae_by_weather.png", dpi=160)
    plt.close(fig)

    print("\nDa luu bang phan tich va 2 bieu do trong reports/.")


if __name__ == "__main__":
    main()