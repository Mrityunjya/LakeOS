from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import polars as pl

from lakeos.profiler.data_profiler import (
    DatasetProfile,
    profile_dataset,
)


@dataclass
class ExecutionReport:
    source_path: str
    output_path: str

    before_files: int
    after_files: int

    before_rows: int
    after_rows: int

    before_size_bytes: int
    after_size_bytes: int

    duplicates_removed: int
    partitions_created: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_optimization(
    profile: DatasetProfile,
    output_path: str | Path,
) -> ExecutionReport:

    source_path = Path(profile.dataset_path)
    output_path = Path(output_path)

    if output_path.exists():
        for file in output_path.rglob("*"):
            if file.is_file():
                file.unlink()
    else:
        output_path.mkdir(parents=True)

    print()
    print("=" * 70)
    print("LAKEOS OPTIMIZATION EXECUTION")
    print("=" * 70)

    print(f"Source : {source_path}")
    print(f"Output : {output_path}")

    # ---------------------------------------------------------
    # 1. Read source data
    # ---------------------------------------------------------

    print()
    print("[1/4] Reading source dataset...")

    df = (
        pl.scan_parquet(str(source_path / "*.parquet"))
        .collect()
    )

    before_rows = df.height

    print(f"Rows loaded: {before_rows:,}")

    # ---------------------------------------------------------
    # 2. Deduplicate
    # ---------------------------------------------------------

    print()
    print("[2/4] Removing duplicate records...")

    before_unique = df.select(
        pl.col("order_id").n_unique()
    ).item()

    df = df.unique(
        subset=["order_id"],
        keep="first",
    )

    after_rows = df.height
    duplicates_removed = before_rows - after_rows

    print(
        f"Duplicates removed: "
        f"{duplicates_removed:,}"
    )

    # ---------------------------------------------------------
    # 3. Create partition columns
    # ---------------------------------------------------------

    print()
    print("[3/4] Creating time-based partitions...")

    df = df.with_columns(
        [
            pl.col("order_timestamp")
            .dt.year()
            .alias("year"),

            pl.col("order_timestamp")
            .dt.month()
            .alias("month"),
        ]
    )

    partitions = (
        df
        .select(["year", "month"])
        .unique()
        .sort(["year", "month"])
    )

    partition_count = partitions.height

    print(
        f"Partitions created: "
        f"{partition_count}"
    )

    # ---------------------------------------------------------
    # 4. Write optimized Parquet files
    # ---------------------------------------------------------

    print()
    print("[4/4] Writing optimized dataset...")

    for row in partitions.iter_rows(named=True):

        year = row["year"]
        month = row["month"]

        partition_df = df.filter(
            (pl.col("year") == year)
            & (pl.col("month") == month)
        )

        partition_dir = (
            output_path
            / f"year={year}"
            / f"month={month:02d}"
        )

        partition_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = (
            partition_dir
            / "data.parquet"
        )

        partition_df.drop(
            ["year", "month"]
        ).write_parquet(
            output_file,
            compression="zstd",
        )

        print(
            f"  {year}-{month:02d} "
            f"-> {partition_df.height:,} rows"
        )

    # ---------------------------------------------------------
    # Calculate after metrics
    # ---------------------------------------------------------

    optimized_profile = profile_dataset(
        output_path
    )

    print()
    print("=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)

    print(
        f"Files      : "
        f"{profile.file_count:,} -> "
        f"{optimized_profile.file_count:,}"
    )

    print(
        f"Rows       : "
        f"{profile.total_rows:,} -> "
        f"{optimized_profile.total_rows:,}"
    )

    print(
        f"Duplicates : "
        f"{profile.duplicate_order_ids:,} -> "
        f"{optimized_profile.duplicate_order_ids:,}"
    )

    print(
        f"Size       : "
        f"{profile.total_size_bytes / (1024 ** 2):.2f} MB -> "
        f"{optimized_profile.total_size_bytes / (1024 ** 2):.2f} MB"
    )

    print("=" * 70)

    return ExecutionReport(
        source_path=str(source_path),
        output_path=str(output_path),

        before_files=profile.file_count,
        after_files=optimized_profile.file_count,

        before_rows=profile.total_rows,
        after_rows=optimized_profile.total_rows,

        before_size_bytes=profile.total_size_bytes,
        after_size_bytes=optimized_profile.total_size_bytes,

        duplicates_removed=duplicates_removed,
        partitions_created=partition_count,
    )