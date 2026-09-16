from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import polars as pl


@dataclass
class FileStats:
    file_name: str
    size_bytes: int
    rows: int


@dataclass
class ColumnStats:
    name: str
    dtype: str
    null_count: int
    null_percentage: float
    unique_count: int


@dataclass
class DatasetProfile:
    dataset_path: str

    file_count: int
    total_size_bytes: int
    average_file_size_bytes: float
    min_file_size_bytes: int
    max_file_size_bytes: int

    total_rows: int

    columns: list[ColumnStats]

    timestamp_min: str | None
    timestamp_max: str | None

    duplicate_order_ids: int

    region_distribution: dict[str, int]

    files: list[FileStats]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# FILE DISCOVERY
# ============================================================

def find_parquet_files(
    dataset_path: Path,
) -> list[Path]:
    """
    Recursively discover all Parquet files.

    Supports both flat and partitioned layouts.
    """

    return sorted(
        dataset_path.rglob("*.parquet")
    )


def parquet_scan_path(
    dataset_path: Path,
) -> str:
    """
    Return a recursive Parquet scan pattern.
    """

    return str(
        dataset_path / "**" / "*.parquet"
    )


# ============================================================
# PHYSICAL FILE PROFILING
# ============================================================

def collect_file_stats(
    dataset_path: Path,
) -> list[FileStats]:
    """Collect physical statistics for every Parquet file."""

    files = find_parquet_files(
        dataset_path
    )

    stats: list[FileStats] = []

    for file in files:

        row_count = (
            pl.scan_parquet(str(file))
            .select(
                pl.len().alias("row_count")
            )
            .collect()
            .item()
        )

        stats.append(
            FileStats(
                file_name=str(
                    file.relative_to(dataset_path)
                ),
                size_bytes=file.stat().st_size,
                rows=int(row_count),
            )
        )

    return stats


# ============================================================
# COLUMN PROFILING
# ============================================================

def profile_columns(
    dataset_path: Path,
) -> list[ColumnStats]:
    """Profile nulls and cardinality for every column."""

    lazy_df = pl.scan_parquet(
        parquet_scan_path(dataset_path)
    )

    schema = lazy_df.collect_schema()

    total_rows = (
        lazy_df
        .select(
            pl.len().alias("total_rows")
        )
        .collect()
        .item()
    )

    expressions = []

    for name in schema.names():

        expressions.append(
            pl.col(name)
            .null_count()
            .alias(
                f"{name}__nulls"
            )
        )

        expressions.append(
            pl.col(name)
            .n_unique()
            .alias(
                f"{name}__unique"
            )
        )

    result = (
        lazy_df
        .select(expressions)
        .collect()
    )

    columns: list[ColumnStats] = []

    for name in schema.names():

        null_count = int(
            result[
                f"{name}__nulls"
            ][0]
        )

        unique_count = int(
            result[
                f"{name}__unique"
            ][0]
        )

        null_percentage = (
            (null_count / total_rows) * 100
            if total_rows
            else 0.0
        )

        columns.append(
            ColumnStats(
                name=name,
                dtype=str(
                    schema[name]
                ),
                null_count=null_count,
                null_percentage=round(
                    null_percentage,
                    2,
                ),
                unique_count=unique_count,
            )
        )

    return columns


# ============================================================
# TIMESTAMP PROFILING
# ============================================================

def profile_timestamp(
    dataset_path: Path,
) -> tuple[str | None, str | None]:
    """Find minimum and maximum order timestamp."""

    lazy_df = pl.scan_parquet(
        parquet_scan_path(dataset_path)
    )

    schema = lazy_df.collect_schema()

    if "order_timestamp" not in schema.names():
        return None, None

    result = (
        lazy_df
        .select(
            [
                pl.col("order_timestamp")
                .min()
                .alias("timestamp_min"),

                pl.col("order_timestamp")
                .max()
                .alias("timestamp_max"),
            ]
        )
        .collect()
    )

    minimum = result[
        "timestamp_min"
    ][0]

    maximum = result[
        "timestamp_max"
    ][0]

    return (
        str(minimum)
        if minimum is not None
        else None,

        str(maximum)
        if maximum is not None
        else None,
    )


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def detect_duplicate_orders(
    dataset_path: Path,
) -> int:
    """Detect duplicate order IDs across the entire dataset."""

    lazy_df = pl.scan_parquet(
        parquet_scan_path(dataset_path)
    )

    schema = lazy_df.collect_schema()

    if "order_id" not in schema.names():
        return 0

    result = (
        lazy_df
        .select(
            [
                pl.len().alias(
                    "total_rows"
                ),

                pl.col("order_id")
                .n_unique()
                .alias(
                    "unique_order_ids"
                ),
            ]
        )
        .collect()
    )

    total_rows = int(
        result["total_rows"][0]
    )

    unique_order_ids = int(
        result["unique_order_ids"][0]
    )

    return max(
        total_rows - unique_order_ids,
        0,
    )


# ============================================================
# REGION PROFILING
# ============================================================

def profile_regions(
    dataset_path: Path,
) -> dict[str, int]:
    """Calculate region frequency distribution."""

    lazy_df = pl.scan_parquet(
        parquet_scan_path(dataset_path)
    )

    schema = lazy_df.collect_schema()

    if "region" not in schema.names():
        return {}

    result = (
        lazy_df
        .group_by("region")
        .agg(
            pl.len().alias("count")
        )
        .sort(
            "count",
            descending=True,
        )
        .collect()
    )

    distribution: dict[str, int] = {}

    for region, count in result.iter_rows():

        region_name = (
            "NULL"
            if region is None
            else str(region)
        )

        distribution[
            region_name
        ] = int(count)

    return distribution


# ============================================================
# COMPLETE DATASET PROFILER
# ============================================================

def profile_dataset(
    dataset_path: str | Path,
) -> DatasetProfile:
    """Run the complete LAKEOS dataset profiling pipeline."""

    dataset_path = Path(
        dataset_path
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: "
            f"{dataset_path}"
        )

    files = find_parquet_files(
        dataset_path
    )

    if not files:
        raise ValueError(
            f"No Parquet files found in "
            f"{dataset_path}"
        )

    print("Scanning dataset...")

    # --------------------------------------------------
    # Physical file profiling
    # --------------------------------------------------

    file_stats = collect_file_stats(
        dataset_path
    )

    total_size = sum(
        file.size_bytes
        for file in file_stats
    )

    total_rows = sum(
        file.rows
        for file in file_stats
    )

    # --------------------------------------------------
    # Logical data profiling
    # --------------------------------------------------

    columns = profile_columns(
        dataset_path
    )

    timestamp_min, timestamp_max = (
        profile_timestamp(
            dataset_path
        )
    )

    duplicate_order_ids = (
        detect_duplicate_orders(
            dataset_path
        )
    )

    region_distribution = (
        profile_regions(
            dataset_path
        )
    )

    return DatasetProfile(
        dataset_path=str(
            dataset_path
        ),

        file_count=len(
            files
        ),

        total_size_bytes=(
            total_size
        ),

        average_file_size_bytes=(
            total_size / len(files)
        ),

        min_file_size_bytes=min(
            file.size_bytes
            for file in file_stats
        ),

        max_file_size_bytes=max(
            file.size_bytes
            for file in file_stats
        ),

        total_rows=total_rows,

        columns=columns,

        timestamp_min=timestamp_min,

        timestamp_max=timestamp_max,

        duplicate_order_ids=(
            duplicate_order_ids
        ),

        region_distribution=(
            region_distribution
        ),

        files=file_stats,
    )


# ============================================================
# HUMAN-READABLE OUTPUT
# ============================================================

def print_profile(
    profile: DatasetProfile,
) -> None:
    """Print a human-readable LAKEOS profile."""

    print()

    print("=" * 65)
    print("LAKEOS DATASET PROFILE")
    print("=" * 65)

    print(
        f"Dataset       : "
        f"{profile.dataset_path}"
    )

    print(
        f"Files         : "
        f"{profile.file_count:,}"
    )

    print(
        f"Rows          : "
        f"{profile.total_rows:,}"
    )

    print(
        f"Total size    : "
        f"{profile.total_size_bytes / (1024 ** 2):.2f} MB"
    )

    print(
        f"Average file  : "
        f"{profile.average_file_size_bytes / 1024:.2f} KB"
    )

    print(
        f"Smallest file : "
        f"{profile.min_file_size_bytes / 1024:.2f} KB"
    )

    print(
        f"Largest file  : "
        f"{profile.max_file_size_bytes / 1024:.2f} KB"
    )

    print()

    print("COLUMNS")
    print("-" * 65)

    for column in profile.columns:

        print(
            f"{column.name:20} "
            f"{column.dtype:18} "
            f"nulls={column.null_percentage:6.2f}% "
            f"unique={column.unique_count:,}"
        )

    print()

    print("TIME RANGE")
    print("-" * 65)

    print(
        f"Min timestamp : "
        f"{profile.timestamp_min}"
    )

    print(
        f"Max timestamp : "
        f"{profile.timestamp_max}"
    )

    print()

    print("DUPLICATES")
    print("-" * 65)

    print(
        f"Duplicate order IDs : "
        f"{profile.duplicate_order_ids:,}"
    )

    print()

    print("REGION DISTRIBUTION")
    print("-" * 65)

    for region, count in (
        profile.region_distribution.items()
    ):

        percentage = (
            count
            / profile.total_rows
            * 100
        )

        print(
            f"{region:15} "
            f"{count:10,} "
            f"({percentage:6.2f}%)"
        )

    print()

    print("=" * 65)

