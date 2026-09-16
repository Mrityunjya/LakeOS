from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import polars as pl

from lakeos.workload.queries import Workload


@dataclass
class BenchmarkResult:
    workload: str
    dataset: str

    execution_time_seconds: float
    median_time_seconds: float
    p95_time_seconds: float
    min_time_seconds: float
    max_time_seconds: float

    trials: int

    rows_returned: int

    file_count: int

    total_size_bytes: int

    # Partition-pruning observability.
    #
    # These values describe the files that are eligible
    # according to Hive-style partition directory metadata.
    # They are not exact engine-level physical scan metrics.
    available_files: int
    eligible_files: int
    pruned_files: int
    pruning_ratio: float

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


def analyze_partition_pruning(
    workload: Workload,
    dataset_path: Path,
) -> dict[str, float | int]:
    """
    Estimate partition pruning using Hive-style
    directory metadata.

    Example:

        year=2025/month=6/data.parquet

    A workload with:

        {"year": 2025, "month": 6}

    will consider only matching files eligible.

    Important:
    These are logical pruning estimates based on
    partition directories. They are not exact
    engine-level bytes/files physically scanned.
    """

    files = find_parquet_files(
        dataset_path
    )

    available_files = len(files)

    if available_files == 0:
        return {
            "available_files": 0,
            "eligible_files": 0,
            "pruned_files": 0,
            "pruning_ratio": 0.0,
        }

    filters = workload.partition_filters

    # No partition metadata associated with
    # the workload means no pruning can be
    # inferred.
    if not filters:
        return {
            "available_files": available_files,
            "eligible_files": available_files,
            "pruned_files": 0,
            "pruning_ratio": 0.0,
        }

    eligible_files = 0

    for file_path in files:

        partition_values: dict[str, str] = {}

        for part in file_path.parts:

            if "=" not in part:
                continue

            key, value = part.split(
                "=",
                1,
            )

            partition_values[key] = value

        matches = True

        for key, expected_value in filters.items():

            actual_value = (
                partition_values.get(key)
            )

            # If the physical layout does not
            # contain this partition key, it
            # cannot be used for pruning.
            #
            # Example:
            # month layout has year/month but
            # does not have region.
            if actual_value is None:
                continue

            if str(actual_value) != str(
                expected_value
            ):
                matches = False
                break

        if matches:
            eligible_files += 1

    pruned_files = (
        available_files
        - eligible_files
    )

    pruning_ratio = (
        pruned_files
        / available_files
        if available_files > 0
        else 0.0
    )

    return {
        "available_files": available_files,
        "eligible_files": eligible_files,
        "pruned_files": pruned_files,
        "pruning_ratio": pruning_ratio,
    }


def calculate_p95(
    timings: list[float],
) -> float:
    """
    Calculate the empirical 95th percentile.

    Uses the nearest-rank approach so that the result
    remains simple and deterministic for small trial counts.
    """

    if not timings:
        return 0.0

    sorted_timings = sorted(timings)

    index = max(
        0,
        int(
            0.95 * len(sorted_timings)
        ) - 1,
    )

    index = min(
        index,
        len(sorted_timings) - 1,
    )

    return sorted_timings[index]


def benchmark_workload(
    workload: Workload,
    dataset_path: str | Path,
    dataset_name: str,
    trials: int = 5,
) -> BenchmarkResult:
    """
    Execute one workload against one dataset.

    Performs:
    - one warmup execution
    - multiple measured trials
    - partition-pruning analysis

    The median execution time is used as the primary
    benchmark measurement.
    """

    if trials < 1:
        raise ValueError(
            "trials must be >= 1"
        )

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

    # --------------------------------------------------------
    # Partition pruning analysis
    # --------------------------------------------------------

    pruning = analyze_partition_pruning(
        workload,
        dataset_path,
    )

    # --------------------------------------------------------
    # Lazy query
    # --------------------------------------------------------

    scan_path = str(
        dataset_path / "**" / "*.parquet"
    )

    lazy_df = pl.scan_parquet(
        scan_path
    )

    query = workload.query(
        lazy_df
    )

    # --------------------------------------------------------
    # Warmup
    # --------------------------------------------------------

    query.collect()

    # --------------------------------------------------------
    # Measured trials
    # --------------------------------------------------------

    timings: list[float] = []

    result = None

    for _ in range(trials):

        start = perf_counter()

        result = query.collect()

        end = perf_counter()

        timings.append(
            end - start
        )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    median_time = median(
        timings
    )

    p95_time = calculate_p95(
        timings
    )

    min_time = min(
        timings
    )

    max_time = max(
        timings
    )

    return BenchmarkResult(
        workload=workload.name,
        dataset=dataset_name,

        # Keep this field for backward compatibility.
        # It now represents the median.
        execution_time_seconds=round(
            median_time,
            6,
        ),

        median_time_seconds=round(
            median_time,
            6,
        ),

        p95_time_seconds=round(
            p95_time,
            6,
        ),

        min_time_seconds=round(
            min_time,
            6,
        ),

        max_time_seconds=round(
            max_time,
            6,
        ),

        trials=trials,

        rows_returned=result.height,

        file_count=len(files),

        total_size_bytes=calculate_dataset_size(
            dataset_path
        ),

        available_files=int(
            pruning["available_files"]
        ),

        eligible_files=int(
            pruning["eligible_files"]
        ),

        pruned_files=int(
            pruning["pruned_files"]
        ),

        pruning_ratio=float(
            pruning["pruning_ratio"]
        ),
    )


def compare_results(
    raw: BenchmarkResult,
    optimized: BenchmarkResult,
) -> dict[str, Any]:
    """Compare raw and optimized benchmark results."""

    raw_time = (
        raw.median_time_seconds
    )

    optimized_time = (
        optimized.median_time_seconds
    )

    if optimized_time > 0:
        speedup = (
            raw_time
            / optimized_time
        )
    else:
        speedup = 0.0

    time_reduction = (
        (
            raw_time
            - optimized_time
        )
        / raw_time
        * 100
        if raw_time > 0
        else 0.0
    )

    return {
        "workload": raw.workload,

        "raw_time_seconds": raw_time,

        "optimized_time_seconds":
            optimized_time,

        "raw_p95_seconds":
            raw.p95_time_seconds,

        "optimized_p95_seconds":
            optimized.p95_time_seconds,

        "speedup": round(
            speedup,
            2,
        ),

        "time_reduction_percentage":
            round(
                time_reduction,
                2,
            ),

        "raw_files":
            raw.file_count,

        "optimized_files":
            optimized.file_count,

        "raw_size_mb":
            round(
                raw.total_size_bytes
                / (1024 ** 2),
                2,
            ),

        "optimized_size_mb":
            round(
                optimized.total_size_bytes
                / (1024 ** 2),
                2,
            ),

        # Partition pruning comparison.
        "raw_available_files":
            raw.available_files,

        "raw_eligible_files":
            raw.eligible_files,

        "raw_pruned_files":
            raw.pruned_files,

        "raw_pruning_ratio":
            round(
                raw.pruning_ratio,
                4,
            ),

        "optimized_available_files":
            optimized.available_files,

        "optimized_eligible_files":
            optimized.eligible_files,

        "optimized_pruned_files":
            optimized.pruned_files,

        "optimized_pruning_ratio":
            round(
                optimized.pruning_ratio,
                4,
            ),

        "trials":
            raw.trials,
    }


def run_benchmark(
    raw_path: str | Path,
    optimized_path: str | Path,
    workloads: list[Workload],
    trials: int = 5,
) -> list[dict[str, Any]]:
    """
    Run all workloads against both datasets.
    """

    comparisons = []

    print()
    print("=" * 75)
    print("LAKEOS WORKLOAD BENCHMARK")
    print("=" * 75)

    print(
        f"Trials per workload: "
        f"{trials}"
    )

    print(
        "Primary metric: median execution time"
    )

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
            trials,
        )

        optimized_result = benchmark_workload(
            workload,
            optimized_path,
            "optimized",
            trials,
        )

        comparison = compare_results(
            raw_result,
            optimized_result,
        )

        comparisons.append(
            comparison
        )

        print(
            f"RAW MEDIAN       : "
            f"{raw_result.median_time_seconds:.6f}s"
        )

        print(
            f"OPTIMIZED MEDIAN : "
            f"{optimized_result.median_time_seconds:.6f}s"
        )

        print(
            f"RAW P95          : "
            f"{raw_result.p95_time_seconds:.6f}s"
        )

        print(
            f"OPTIMIZED P95    : "
            f"{optimized_result.p95_time_seconds:.6f}s"
        )

        print(
            f"SPEEDUP          : "
            f"{comparison['speedup']:.2f}x"
        )

        print(
            f"TIME RED.        : "
            f"{comparison['time_reduction_percentage']:.2f}%"
        )

        print(
            f"FILES            : "
            f"{raw_result.file_count} -> "
            f"{optimized_result.file_count}"
        )

        print(
            f"PRUNING          : "
            f"{optimized_result.eligible_files}/"
            f"{optimized_result.available_files} "
            f"eligible, "
            f"{optimized_result.pruned_files} "
            f"pruned "
            f"({optimized_result.pruning_ratio:.2%})"
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
            f"Raw P95  : "
            f"{comparison['raw_p95_seconds']:.6f}s"
        )

        print(
            f"Opt P95  : "
            f"{comparison['optimized_p95_seconds']:.6f}s"
        )

        print(
            f"Speedup  : "
            f"{comparison['speedup']:.2f}x"
        )

        print(
            f"Reduction: "
            f"{comparison['time_reduction_percentage']:.2f}%"
        )

        print(
            f"Trials   : "
            f"{comparison['trials']}"
        )

        print(
            f"Pruning  : "
            f"{comparison['optimized_eligible_files']}/"
            f"{comparison['optimized_available_files']} "
            f"eligible"
        )

        print(
            f"Pruned   : "
            f"{comparison['optimized_pruned_files']} "
            f"files "
            f"({comparison['optimized_pruning_ratio']:.2%})"
        )

    print()
    print("=" * 75)