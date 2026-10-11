from data import PROJECT_ROOT, load_data


VALIDATION_START = "2012-05-01"
TEST_START = "2012-09-01"


def split_by_time(df):
    train = df[df["timestamp"] < VALIDATION_START].copy()

    validation = df[
        (df["timestamp"] >= VALIDATION_START)
        & (df["timestamp"] < TEST_START)
    ].copy()

    test = df[df["timestamp"] >= TEST_START].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError("Co tap du lieu rong. Hay kiem tra moc chia.")

    assert train["timestamp"].max() < validation["timestamp"].min()
    assert validation["timestamp"].max() < test["timestamp"].min()
    assert len(train) + len(validation) + len(test) == len(df)

    return train, validation, test


def main():
    df = load_data()
    train, validation, test = split_by_time(df)

    output_dir = PROJECT_ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "train": train,
        "validation": validation,
        "test": test,
    }

    for name, dataset in datasets.items():
        output_path = output_dir / f"{name}.csv"
        dataset.to_csv(output_path, index=False)

        print(f"\n=== {name.upper()} ===")
        print(f"So dong: {len(dataset)}")
        print(f"Bat dau: {dataset['timestamp'].min()}")
        print(f"Ket thuc: {dataset['timestamp'].max()}")

    print("\nDa luu 3 tap vao data/processed")


if __name__ == "__main__":
    main()