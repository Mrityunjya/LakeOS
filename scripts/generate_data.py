from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_DIR = Path("data/sample/orders")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(42)

NUM_RECORDS = 1_000_000
NUM_FILES = 100


def generate_orders(num_records: int) -> pd.DataFrame:
    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2026-01-01")

    timestamps = pd.to_datetime(
        RNG.integers(
            start.value,
            end.value,
            size=num_records,
        )
    )

    df = pd.DataFrame(
        {
            "order_id": np.arange(1, num_records + 1),
            "customer_id": RNG.integers(1, 250_000, num_records),
            "product_id": RNG.integers(1, 50_000, num_records),
            "order_timestamp": timestamps,
            "region": RNG.choice(
                [
                    "Chennai",
                    "Bengaluru",
                    "Mumbai",
                    "Delhi",
                    "Hyderabad",
                ],
                size=num_records,
                p=[0.45, 0.20, 0.15, 0.12, 0.08],
            ),
            "payment_method": RNG.choice(
                [
                    "UPI",
                    "Card",
                    "NetBanking",
                    "Wallet",
                    "COD",
                ],
                size=num_records,
                p=[0.45, 0.25, 0.12, 0.08, 0.10],
            ),
            "status": RNG.choice(
                [
                    "completed",
                    "cancelled",
                    "returned",
                    "pending",
                ],
                size=num_records,
                p=[0.78, 0.08, 0.07, 0.07],
            ),
            "quantity": RNG.integers(1, 6, num_records),
            "order_amount": np.round(
                RNG.lognormal(
                    mean=7.0,
                    sigma=0.8,
                    size=num_records,
                ),
                2,
            ),
        }
    )

    # 2% missing payment methods
    null_indices = RNG.choice(
        num_records,
        size=20_000,
        replace=False,
    )

    df.loc[null_indices, "payment_method"] = None

    return df


def main():
    print("Generating LAKEOS dataset...")

    df = generate_orders(NUM_RECORDS)

    # Divide the DataFrame into 100 pieces.
    chunks = np.array_split(
        df.index.to_numpy(),
        NUM_FILES,
    )

    for i, indices in enumerate(chunks):
        chunk = df.loc[indices].copy()

        output_file = (
            OUTPUT_DIR / f"orders_{i:04d}.parquet"
        )

        chunk.to_parquet(
            output_file,
            index=False,
            engine="pyarrow",
        )

        print(
            f"Created {i + 1:03d}/{NUM_FILES}: "
            f"{output_file.name}"
        )

    # Intentional duplicates.
    duplicates = df.sample(
        n=5_000,
        random_state=42,
    )

    duplicates.to_parquet(
        OUTPUT_DIR / "orders_duplicates.parquet",
        index=False,
        engine="pyarrow",
    )

    parquet_files = list(
        OUTPUT_DIR.glob("*.parquet")
    )

    print()
    print("===================================")
    print("LAKEOS DATASET GENERATED")
    print("===================================")
    print(f"Original records : {len(df):,}")
    print("Duplicate records: 5,000")
    print(f"Parquet files    : {len(parquet_files)}")
    print(f"Output directory : {OUTPUT_DIR}")
    print("===================================")


if __name__ == "__main__":
    main()