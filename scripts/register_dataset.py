from pathlib import Path

import polars as pl

from lakeos.metadata.catalog import (
    print_catalog,
    register_dataset,
)
from lakeos.optimizer.execution_engine import (
    calculate_size,
    find_parquet_files,
)


DATASET_PATH = Path(
    "data/lake/optimized/orders"
)


def main():
    files = find_parquet_files(
        DATASET_PATH
    )

    if not files:
        raise ValueError(
            f"No Parquet files found in "
            f"{DATASET_PATH}"
        )

    total_rows = 0

    for file in files:
        total_rows += (
            pl.scan_parquet(
                str(file)
            )
            .select(
                pl.len()
            )
            .collect()
            .item()
        )

    metadata = register_dataset(
        dataset_name="orders",
        dataset_path=DATASET_PATH,
        layout="month",
        file_count=len(files),
        total_rows=total_rows,
        total_size_bytes=calculate_size(
            DATASET_PATH
        ),
    )

    print()

    print(
        f"Registered dataset: "
        f"{metadata.dataset_name}"
    )

    print_catalog()


if __name__ == "__main__":
    main()