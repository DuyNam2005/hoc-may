from pathlib import Path

import pandas as pd


# Xác định thư mục dự án từ vị trí của tệp này.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "hour.csv"


def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Khong tim thay tep: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    # Ghép ngày và giờ thành một mốc thời gian.
    df["timestamp"] = (
        pd.to_datetime(df["dteday"], format="%Y-%m-%d")
        + pd.to_timedelta(df["hr"], unit="h")
    )

    return df.sort_values("timestamp").reset_index(drop=True)


def main():
    df = load_data()

    print("=== KIEM TRA DU LIEU ===")
    print(f"So dong: {len(df)}")
    print(f"So cot goc: {len(df.columns) - 1}")
    print(f"Bat dau: {df['timestamp'].min()}")
    print(f"Ket thuc: {df['timestamp'].max()}")
    print(f"So o thieu: {df.isna().sum().sum()}")
    print(f"So moc gio trung: {df['timestamp'].duplicated().sum()}")

    expected_hours = pd.date_range(
        start=df["timestamp"].min(),
        end=df["timestamp"].max(),
        freq="h",
    )
    missing_hours = expected_hours.difference(
        pd.DatetimeIndex(df["timestamp"])
    )
    print(f"So moc gio thieu: {len(missing_hours)}")

    print("\n5 dong dau:")
    print(df[["timestamp", "weathersit", "temp", "hum", "cnt"]].head())


if __name__ == "__main__":
    main()