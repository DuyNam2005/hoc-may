import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from baseline import calculate_metrics, predict_baseline
from data import PROJECT_ROOT
from features import FEATURE_COLUMNS, build_preprocessor


SEED = 42


def evaluate_split(train, validation, split_name):
    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("model", LinearRegression()),
    ])

    # Tiền xử lý chỉ fit trên train của từng thí nghiệm.
    pipeline.fit(train[FEATURE_COLUMNS], train["cnt"])

    linear_predictions = pipeline.predict(
        validation[FEATURE_COLUMNS]
    )
    baseline_predictions = predict_baseline(
        train,
        validation[["weekday", "hr"]],
    )

    rows = []

    for model_name, predictions in [
        ("Baseline", baseline_predictions),
        ("LinearRegression", linear_predictions),
    ]:
        rows.append({
            "split": split_name,
            "model": model_name,
            "train_rows": len(train),
            "validation_rows": len(validation),
            **calculate_metrics(validation["cnt"], predictions),
        })

    return rows


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    time_train = pd.read_csv(
        data_dir / "train.csv",
        parse_dates=["timestamp"],
    )
    time_validation = pd.read_csv(
        data_dir / "validation.csv",
        parse_dates=["timestamp"],
    )

    # Không đọc test.csv.
    development_data = pd.concat(
        [time_train, time_validation],
        ignore_index=True,
    )

    # Giữ cùng số dòng train/validation như time split.
    rng = np.random.default_rng(SEED)
    shuffled_indices = rng.permutation(len(development_data))
    validation_size = len(time_validation)

    random_validation = development_data.iloc[
        shuffled_indices[:validation_size]
    ].copy()

    random_train = development_data.iloc[
        shuffled_indices[validation_size:]
    ].copy()

    results = []
    results.extend(
        evaluate_split(time_train, time_validation, "time")
    )
    results.extend(
        evaluate_split(random_train, random_validation, "random")
    )

    results_df = pd.DataFrame(results)

    print("=== SO SANH CACH CHIA DU LIEU ===")
    print(results_df.to_string(index=False, float_format="%.4f"))

    results_df.to_csv(
        reports_dir / "split_comparison.csv",
        index=False,
    )

    config = {
        "seed": SEED,
        "data_scope": "original_train_and_validation_only",
        "final_test_used": False,
        "train_rows": len(time_train),
        "validation_rows": validation_size,
        "purpose": "illustration_only",
    }

    with (reports_dir / "split_experiment_config.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(config, file, indent=2)

    print("\nDa luu ket qua. Test cuoi van duoc giu nguyen.")


if __name__ == "__main__":
    main()