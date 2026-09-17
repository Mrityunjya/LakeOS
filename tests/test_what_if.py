from pathlib import Path

from lakeos.optimizer.what_if import (
    estimate_partition_pruning,
    evaluate_layouts,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
)


DATASET_PATH = Path("data/sample/orders")


def test_month_layout_has_pruning_for_time_workload():
    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    profile = next(
        profile
        for profile in profiles
        if profile.name == "monthly_orders"
    )

    result = estimate_partition_pruning(
        profile,
        "month",
    )

    assert result["pruning_ratio"] > 0
    assert result["pruned_files"] > 0


def test_none_layout_has_no_pruning():
    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    profile = next(
        profile
        for profile in profiles
        if profile.name == "monthly_orders"
    )

    result = estimate_partition_pruning(
        profile,
        "none",
    )

    assert result["pruning_ratio"] == 0.0
    assert result["pruned_files"] == 0


def test_full_scan_does_not_receive_pruning_bonus():
    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    profile = next(
        profile
        for profile in profiles
        if profile.name == "revenue_by_region"
    )

    results = evaluate_layouts(profile)

    none_result = next(
        result
        for result in results
        if result.layout == "none"
    )

    month_result = next(
        result
        for result in results
        if result.layout == "month"
    )

    assert (
        month_result.pruning_score == 0.0
        or month_result.predicted_cost
        >= none_result.predicted_cost
    )