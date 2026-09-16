from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import polars as pl

from lakeos.workload.queries import (
    Workload,
)


@dataclass
class BenchmarkResult:
    workload: str
    dataset: str

    execution_time_seconds: float

    rows_returned: int

    file_count: int

    total_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_parquet_files(
    dataset_path: Path,
) -> list[Path]:
    """Find all Parquet files recursively."""

    return sorted(
        dataset_path.rglob("*.parquet")
    )


def calculate_dataset_size(
    dataset_path: Path,
) -> int:
    """Calculate total physical dataset size."""

    return sum(
        file.stat().st_size
        for file in find_parquet_files(
            dataset_path
        )
    )


def benchmark_workload(
    workload: Workload,
    dataset_path: str | Path,
    dataset_name: str,
) -> BenchmarkResult:
    """
    Execute one workload against one dataset
    and measure execution time.
    """

    dataset_path = Path(
        dataset_path
    )

    files = find_parquet_files(
        dataset_path
    )

    if not files:
        raise ValueError(
            f"No Parquet files found in "
            f"{dataset_path}"
        )

    scan_path = str(
        dataset_path / "**" / "*.parquet"
    )

    lazy_df = pl.scan_parquet(
        scan_path
    )

    query = workload.query(
        lazy_df
    )

    start = perf_counter()

    result = query.collect()

    end = perf_counter()

    execution_time = end - start

    return BenchmarkResult(
        workload=workload.name,
        dataset=dataset_name,
        execution_time_seconds=round(
            execution_time,
            6,
        ),
        rows_returned=result.height,
        file_count=len(files),
        total_size_bytes=calculate_dataset_size(
            dataset_path
        ),
    )


def compare_results(
    raw: BenchmarkResult,
    optimized: BenchmarkResult,
) -> dict[str, Any]:
    """Compare raw and optimized benchmark results."""

    raw_time = raw.execution_time_seconds
    optimized_time = (
        optimized.execution_time_seconds
    )

    if optimized_time > 0:
        speedup = (
            raw_time / optimized_time
        )
    else:
        speedup = 0.0

    time_reduction = (
        (
            raw_time - optimized_time
        )
        / raw_time
        * 100
        if raw_time > 0
        else 0.0
    )

    return {
        "workload": raw.workload,
        "raw_time_seconds": raw_time,
        "optimized_time_seconds": optimized_time,
        "speedup": round(
            speedup,
            2,
        ),
        "time_reduction_percentage": round(
            time_reduction,
            2,
        ),
        "raw_files": raw.file_count,
        "optimized_files": optimized.file_count,
        "raw_size_mb": round(
            raw.total_size_bytes
            / (1024 ** 2),
            2,
        ),
        "optimized_size_mb": round(
            optimized.total_size_bytes
            / (1024 ** 2),
            2,
        ),
    }


def run_benchmark(
    raw_path: str | Path,
    optimized_path: str | Path,
    workloads: list[Workload],
) -> list[dict[str, Any]]:
    """
    Run all workloads against both datasets.
    """

    comparisons = []

    print()
    print("=" * 75)
    print("LAKEOS WORKLOAD BENCHMARK")
    print("=" * 75)

    for workload in workloads:

        print()
        print(
            f"WORKLOAD: "
            f"{workload.name}"
        )

        print(
            f"Description: "
            f"{workload.description}"
        )

        print("-" * 75)

        raw_result = benchmark_workload(
            workload,
            raw_path,
            "raw",
        )

        optimized_result = benchmark_workload(
            workload,
            optimized_path,
            "optimized",
        )

        comparison = compare_results(
            raw_result,
            optimized_result,
        )

        comparisons.append(
            comparison
        )

        print(
            f"RAW       : "
            f"{raw_result.execution_time_seconds:.6f}s"
        )

        print(
            f"OPTIMIZED : "
            f"{optimized_result.execution_time_seconds:.6f}s"
        )

        print(
            f"SPEEDUP   : "
            f"{comparison['speedup']:.2f}x"
        )

        print(
            f"TIME RED. : "
            f"{comparison['time_reduction_percentage']:.2f}%"
        )

        print(
            f"FILES     : "
            f"{raw_result.file_count} -> "
            f"{optimized_result.file_count}"
        )

    print()
    print("=" * 75)

    return comparisons


def print_benchmark_summary(
    comparisons: list[dict[str, Any]],
) -> None:
    """Print a compact benchmark summary."""

    print()
    print("=" * 75)
    print("LAKEOS BENCHMARK SUMMARY")
    print("=" * 75)

    for comparison in comparisons:

        print()
        print(
            f"Workload : "
            f"{comparison['workload']}"
        )

        print(
            f"Raw      : "
            f"{comparison['raw_time_seconds']:.6f}s"
        )

        print(
            f"Optimized: "
            f"{comparison['optimized_time_seconds']:.6f}s"
        )

        print(
            f"Speedup  : "
            f"{comparison['speedup']:.2f}x"
        )

        print(
            f"Reduction: "
            f"{comparison['time_reduction_percentage']:.2f}%"
        )

    print()
    print("=" * 75)

