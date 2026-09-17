from pathlib import Path

from lakeos.workload.benchmark import (
    benchmark_workload,
)
from lakeos.workload.queries import (
    WORKLOADS,
)


DATASET_PATH = Path("data/sample/orders")


def test_workload_registry_contains_expected_workloads():
    names = {
        workload.name
        for workload in WORKLOADS
    }

    assert names == {
        "monthly_orders",
        "regional_monthly_orders",
        "revenue_by_region",
    }


def test_monthly_workload_returns_result():
    workload = next(
        workload
        for workload in WORKLOADS
        if workload.name == "monthly_orders"
    )

    result = benchmark_workload(
        workload=workload,
        dataset_path=DATASET_PATH,
        dataset_name="raw",
        trials=1,
    )

    assert result.rows_returned == 1
    assert result.median_time_seconds > 0


def test_partition_pruning_metadata_is_detected():
    workload = next(
        workload
        for workload in WORKLOADS
        if workload.name == "monthly_orders"
    )

    result = benchmark_workload(
        workload=workload,
        dataset_path=DATASET_PATH,
        dataset_name="raw",
        trials=1,
    )

    assert result.available_files == 101
    assert result.eligible_files == 101
    assert result.pruned_files == 0