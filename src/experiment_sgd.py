import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDRegressor
from sklearn.pipeline import Pipeline

from baseline import calculate_metrics
from data import PROJECT_ROOT
from features import FEATURE_COLUMNS, build_preprocessor


LEARNING_RATES = [0.0001, 0.001, 0.01]
EPOCHS = 200
SEED = 42


def main():
    data_dir = PROJECT_ROOT / "data" / "processed"
    reports_dir = PROJECT_ROOT / "reports"
    figures_dir = reports_dir / "figures"
    models_dir = PROJECT_ROOT / "models"

    figures_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(data_dir / "train.csv")
    validation = pd.read_csv(data_dir / "validation.csv")

    # Tiền xử lý chỉ học từ train.
    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(train[FEATURE_COLUMNS])
    X_validation = preprocessor.transform(
        validation[FEATURE_COLUMNS]
    )

    y_train = train["cnt"].to_numpy()
    y_validation = validation["cnt"].to_numpy()

    results = []
    history = []

    for rate in LEARNING_RATES:
        print(f"Dang train SGD voi learning rate = {rate}")

        model = SGDRegressor(
            loss="squared_error",
            penalty=None,
            learning_rate="constant",
            eta0=rate,
            shuffle=False,
            random_state=SEED,
            average=False,
        )

        # Khởi tạo lại RNG để cả ba cấu hình dùng cùng
        # thứ tự mẫu trong từng vòng học.
        rng = np.random.default_rng(SEED)

        for epoch in range(1, EPOCHS + 1):
            order = rng.permutation(len(y_train))
            model.partial_fit(X_train[order], y_train[order])

            train_prediction = model.predict(X_train)
            validation_prediction = model.predict(X_validation)

            if not (
                np.isfinite(train_prediction).all()
                and np.isfinite(validation_prediction).all()
            ):
                raise ValueError(
                    f"SGD khong on dinh voi learning rate {rate}"
                )

            train_rmse = float(
                np.sqrt(np.mean((y_train - train_prediction) ** 2))
            )
            validation_rmse = float(
                np.sqrt(
                    np.mean(
                        (y_validation - validation_prediction) ** 2
                    )
                )
            )

            history.append({
                "learning_rate": rate,
                "epoch": epoch,
                "train_RMSE": train_rmse,
                "validation_RMSE": validation_rmse,
            })

        metrics = calculate_metrics(
            y_validation,
            validation_prediction,
        )
        results.append({
            "learning_rate": rate,
            "epochs": EPOCHS,
            "seed": SEED,
            **metrics,
        })

        # Ghép các bước đã học thành pipeline để lưu.
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])
        joblib.dump(
            pipeline,
            models_dir / f"sgd_candidate_{rate}.joblib",
        )

    results_df = pd.DataFrame(results)
    history_df = pd.DataFrame(history)

    print("\n=== SGD TREN VALIDATION SAU 200 VONG ===")
    print(results_df.to_string(index=False, float_format="%.4f"))

    results_df.to_csv(
        reports_dir / "sgd_validation_metrics.csv",
        index=False,
    )
    history_df.to_csv(
        reports_dir / "sgd_learning_history.csv",
        index=False,
    )

    config = {
        "learning_rates": LEARNING_RATES,
        "epochs": EPOCHS,
        "seed": SEED,
        "loss": "squared_error",
        "penalty": None,
        "learning_rate_schedule": "constant",
        "evaluation_split": "validation",
        "prediction_policy": "raw_unrounded",
        "features": FEATURE_COLUMNS,
    }
    with (reports_dir / "sgd_config.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(config, file, indent=2)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for rate in LEARNING_RATES:
        curve = history_df[
            history_df["learning_rate"] == rate
        ]
        axes[0].plot(
            curve["epoch"],
            curve["train_RMSE"],
            label=f"lr={rate}",
        )
        axes[1].plot(
            curve["epoch"],
            curve["validation_RMSE"],
            label=f"lr={rate}",
        )

    for axis, title in zip(
        axes,
        ["Training RMSE", "Validation RMSE"],
    ):
        axis.set_title(title)
        axis.set_xlabel("Epoch")
        axis.set_ylabel("RMSE (rentals/hour)")
        axis.grid(alpha=0.3)
        axis.legend()

    fig.tight_layout()
    fig.savefig(
        figures_dir / "sgd_learning_curves.png",
        dpi=160,
    )
    plt.close(fig)

    print("\nDa luu bang ket qua, lich su hoc va bieu do.")


if __name__ == "__main__":
    main()