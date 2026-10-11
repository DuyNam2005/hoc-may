import json

import matplotlib.pyplot as plt
import pandas as pd

from data import PROJECT_ROOT, load_data


def main():
    reports_dir = PROJECT_ROOT / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Kiểm tra cấu trúc và chất lượng dữ liệu gốc.
    raw = load_data()

    expected_hours = pd.date_range(
        raw["timestamp"].min(),
        raw["timestamp"].max(),
        freq="h",
    )
    missing_hours = expected_hours.difference(
        pd.DatetimeIndex(raw["timestamp"])
    )

    quality = {
        "file": "hour.csv",
        "rows": len(raw),
        "original_columns": len(raw.columns) - 1,
        "missing_cells": int(raw.isna().sum().sum()),
        "duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_timestamps": int(
            raw["timestamp"].duplicated().sum()
        ),
        "missing_hours": len(missing_hours),
        "start": str(raw["timestamp"].min()),
        "end": str(raw["timestamp"].max()),
        "target_sum_consistent": bool(
            (raw["casual"] + raw["registered"] == raw["cnt"]).all()
        ),
        "removed_rows": 0,
        "missing_hour_policy": "keep_missing_do_not_fill_with_zero",
    }

    with (reports_dir / "data_quality.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(quality, file, indent=2)

    pd.DataFrame({
        "timestamp": missing_hours
    }).to_csv(
        reports_dir / "missing_hours.csv",
        index=False,
    )

    # Khám phá phân bố và ngoại lệ chỉ trên train.
    train = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "train.csv"
    )

    q1 = float(train["cnt"].quantile(0.25))
    q3 = float(train["cnt"].quantile(0.75))
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_mask = (
        (train["cnt"] < lower) | (train["cnt"] > upper)
    )

    train_summary = {
        "scope": "train_only",
        "target_statistics": {
            key: float(value)
            for key, value in train["cnt"].describe().items()
        },
        "iqr_lower_bound": lower,
        "iqr_upper_bound": upper,
        "iqr_flagged_rows": int(outlier_mask.sum()),
        "outlier_policy": "flag_for_review_keep_all_rows",
        "weather_counts": {
            str(key): int(value)
            for key, value in (
                train["weathersit"].value_counts().sort_index().items()
            )
        },
    }

    with (reports_dir / "train_eda_summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(train_summary, file, indent=2)

    train.loc[
        outlier_mask, ["timestamp", "hr", "weathersit", "cnt"]
    ].to_csv(
        reports_dir / "train_iqr_flagged_rows.csv",
        index=False,
    )

    # Biểu đồ 1: phân bố lượt thuê trên train.
    fig, axis = plt.subplots(figsize=(8, 4))
    axis.hist(
        train["cnt"],
        bins=40,
        color="#08776e",
        edgecolor="white",
    )
    axis.set_title("Training target distribution")
    axis.set_xlabel("Rentals/hour")
    axis.set_ylabel("Number of observations")
    fig.tight_layout()
    fig.savefig(
        figures_dir / "train_target_distribution.png",
        dpi=160,
    )
    plt.close(fig)

    # Biểu đồ 2: nhu cầu theo giờ và loại ngày.
    hourly = train.groupby(
        ["hr", "workingday"]
    )["cnt"].mean().unstack("workingday")

    fig, axis = plt.subplots(figsize=(10, 4))
    for code, label in [
        (0, "Weekend or holiday"),
        (1, "Working day"),
    ]:
        if code in hourly.columns:
            axis.plot(
                hourly.index,
                hourly[code],
                marker="o",
                label=label,
            )

    axis.set_title("Training mean demand by hour and day type")
    axis.set_xlabel("Hour")
    axis.set_ylabel("Mean rentals/hour")
    axis.set_xticks(range(24))
    axis.grid(alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(
        figures_dir / "train_demand_by_hour.png",
        dpi=160,
    )
    plt.close(fig)

    # Biểu đồ 3: số mẫu theo nhóm thời tiết.
    weather_counts = (
        train["weathersit"]
        .value_counts()
        .reindex([1, 2, 3, 4], fill_value=0)
    )

    fig, axis = plt.subplots(figsize=(8, 4))
    axis.bar(
        weather_counts.index.astype(str),
        weather_counts.values,
        color="#08776e",
    )
    for index, value in enumerate(weather_counts.values):
        axis.text(
            index, value, str(value),
            ha="center", va="bottom",
        )

    axis.set_title("Training observations by weather")
    axis.set_xlabel("Weather code")
    axis.set_ylabel("Number of observations")
    axis.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(
        figures_dir / "train_weather_counts.png",
        dpi=160,
    )
    plt.close(fig)

    print("=== BAO CAO CHAT LUONG DU LIEU ===")
    print(f"So dong: {quality['rows']}")
    print(f"So o thieu: {quality['missing_cells']}")
    print(f"So moc gio thieu: {quality['missing_hours']}")
    print(f"So dong bi loai: {quality['removed_rows']}")

    print("\n=== EDA TREN TRAIN ===")
    print(f"So dong gan co theo IQR: {int(outlier_mask.sum())}")
    print("Chi gan co de xem xet, khong tu dong loai.")
    print("So mau thoi tiet:", train_summary["weather_counts"])
    print("\nDa luu bao cao va 3 bieu do trong reports/.")


if __name__ == "__main__":
    main()