from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass
class ExecutionReport:
    source_path: str
    output_path: str

    layout: str

    input_rows: int
    output_rows: int

    duplicates_removed: int

    partitions_created: int

    output_files: int
    output_size_bytes: int


# ============================================================
# FILE UTILITIES
# ============================================================

def find_parquet_files(
    dataset_path: Path,
) -> list[Path]:
    """Find Parquet files recursively."""

    return sorted(
        dataset_path.rglob("*.parquet")
    )


def calculate_size(
    dataset_path: Path,
) -> int:
    """Calculate total size of a dataset."""

    return sum(
        file.stat().st_size
        for file in find_parquet_files(
            dataset_path
        )
    )


# ============================================================
# DATA LOADING
# ============================================================

def load_dataset(
    dataset_path: Path,
) -> pl.DataFrame:
    """Load all Parquet data into a DataFrame."""

    files = find_parquet_files(
        dataset_path
    )

    if not files:
        raise ValueError(
            f"No Parquet files found in "
            f"{dataset_path}"
        )

    return (
        pl.scan_parquet(
            [
                str(file)
                for file in files
            ]
        )
        .collect()
    )


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_dataset(
    df: pl.DataFrame,
) -> tuple[pl.DataFrame, int]:
    """
    Remove duplicate logical records using order_id.
    """

    if "order_id" not in df.columns:

        return df, 0

    before = df.height

    df = df.unique(
        subset=["order_id"],
        keep="first",
    )

    removed = (
        before
        - df.height
    )

    return df, removed


# ============================================================
# LAYOUT: NONE
# ============================================================

def write_unpartitioned(
    df: pl.DataFrame,
    output_path: Path,
) -> int:
    """
    Write a compact unpartitioned Parquet dataset.
    """

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_path
        / "data.parquet"
    )

    df.write_parquet(
        output_file,
        compression="zstd",
    )

    return 1


# ============================================================
# LAYOUT: MONTH
# ============================================================

def write_month_partitioned(
    df: pl.DataFrame,
    output_path: Path,
) -> int:
    """
    Write data partitioned by year/month.
    """

    if "order_timestamp" not in df.columns:

        raise ValueError(
            "Month partitioning requires "
            "'order_timestamp'."
        )

    df = (
        df
        .with_columns(
            [
                pl.col(
                    "order_timestamp"
                )
                .dt.year()
                .alias("year"),

                pl.col(
                    "order_timestamp"
                )
                .dt.month()
                .alias("month"),
            ]
        )
    )

    partition_count = 0

    for (
        year,
        month,
    ), partition in df.partition_by(
        ["year", "month"],
        as_dict=True,
    ).items():

        partition_path = (
            output_path
            / f"year={year}"
            / f"month={month:02d}"
        )

        partition_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        partition = partition.drop(
            ["year", "month"]
        )

        partition.write_parquet(
            partition_path
            / "data.parquet",
            compression="zstd",
        )

        partition_count += 1

    return partition_count


# ============================================================
# LAYOUT: MONTH + REGION
# ============================================================

def write_month_region_partitioned(
    df: pl.DataFrame,
    output_path: Path,
) -> int:
    """
    Write data partitioned by year/month/region.
    """

    required_columns = {
        "order_timestamp",
        "region",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            "Month + region partitioning "
            f"requires columns: {missing}"
        )

    df = (
        df
        .with_columns(
            [
                pl.col(
                    "order_timestamp"
                )
                .dt.year()
                .alias("year"),

                pl.col(
                    "order_timestamp"
                )
                .dt.month()
                .alias("month"),
            ]
        )
    )

    partition_count = 0

    for (
        year,
        month,
        region,
    ), partition in df.partition_by(
        [
            "year",
            "month",
            "region",
        ],
        as_dict=True,
    ).items():

        safe_region = str(
            region
        ).replace(
            "/",
            "_",
        )

        partition_path = (
            output_path
            / f"year={year}"
            / f"month={month:02d}"
            / f"region={safe_region}"
        )

        partition_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        partition = partition.drop(
            ["year", "month"]
        )

        partition.write_parquet(
            partition_path
            / "data.parquet",
            compression="zstd",
        )

        partition_count += 1

    return partition_count


# ============================================================
# LAYOUT DISPATCH
# ============================================================

def execute_layout(
    df: pl.DataFrame,
    layout: str,
    output_path: Path,
) -> int:
    """
    Execute the physical layout selected by LAKEOS.
    """

    if layout == "none":

        return write_unpartitioned(
            df,
            output_path,
        )

    if layout == "month":

        return write_month_partitioned(
            df,
            output_path,
        )

    if layout == "month_region":

        return write_month_region_partitioned(
            df,
            output_path,
        )

    raise ValueError(
        f"Unsupported layout: {layout}"
    )


# ============================================================
# MAIN EXECUTION
# ============================================================

def execute_optimization(
    source_path: str | Path,
    output_path: str | Path,
    layout: str,
) -> ExecutionReport:
    """
    Execute a workload-selected physical layout.
    """

    source_path = Path(
        source_path
    )

    output_path = Path(
        output_path
    )

    print()
    print("=" * 75)
    print("LAKEOS LAYOUT-AWARE EXECUTION")
    print("=" * 75)

    print(
        f"Source layout : raw"
    )

    print(
        f"Target layout : {layout}"
    )

    print(
        f"Output path   : {output_path}"
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_dataset(
        source_path
    )

    input_rows = df.height

    print(
        f"Rows loaded   : "
        f"{input_rows:,}"
    )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    df, duplicates_removed = (
        deduplicate_dataset(df)
    )

    print(
        f"Duplicates removed: "
        f"{duplicates_removed:,}"
    )

    # --------------------------------------------------------
    # Clean previous output
    # --------------------------------------------------------

    if output_path.exists():

        for file in (
            output_path.rglob("*")
        ):

            if file.is_file():
                file.unlink()

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Execute selected layout
    # --------------------------------------------------------

    partitions_created = execute_layout(
        df,
        layout,
        output_path,
    )

    output_files = len(
        find_parquet_files(
            output_path
        )
    )

    output_size = calculate_size(
        output_path
    )

    print(
        f"Partitions created: "
        f"{partitions_created:,}"
    )

    print(
        f"Output files     : "
        f"{output_files:,}"
    )

    print(
        f"Output size      : "
        f"{output_size / (1024 ** 2):.2f} MB"
    )

    print()
    print("=" * 75)

    return ExecutionReport(
        source_path=str(
            source_path
        ),

        output_path=str(
            output_path
        ),

        layout=layout,

        input_rows=input_rows,

        output_rows=df.height,

        duplicates_removed=(
            duplicates_removed
        ),

        partitions_created=(
            partitions_created
        ),

        output_files=output_files,

        output_size_bytes=output_size,
    )