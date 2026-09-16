import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPORT_PATH = Path(
    "data/lakeos_optimization_report.json"
)


@dataclass
class WorkloadReport:
    workload: str
    frequency: float

    baseline_time_seconds: float
    selected_time_seconds: float

    median_improvement_percentage: float
    p95_improvement_percentage: float

    predicted_cost: float
    actual_relative_cost: float
    prediction_error_percentage: float


@dataclass
class OptimizationReport:
    run_id: str
    selected_layout: str

    candidate_layouts: list[str]

    baseline_files: int
    selected_files: int

    baseline_size_bytes: int
    selected_size_bytes: int

    file_count_change_percentage: float
    storage_change_percentage: float

    workload_weighted_improvement_percentage: float

    workloads: list[WorkloadReport]

    decision_reason: str

    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_percentage_change(
    baseline: float,
    current: float,
) -> float:

    if baseline <= 0:
        return 0.0

    return round(
        (
            baseline - current
        )
        / baseline
        * 100,
        2,
    )


def calculate_file_count_change(
    baseline_files: int,
    selected_files: int,
) -> float:

    if baseline_files <= 0:
        return 0.0

    return round(
        (
            selected_files
            - baseline_files
        )
        / baseline_files
        * 100,
        2,
    )


def calculate_storage_change(
    baseline: int,
    current: int,
) -> float:

    if baseline <= 0:
        return 0.0

    return round(
        (
            current - baseline
        )
        / baseline
        * 100,
        2,
    )


def calculate_workload_weighted_improvement(
    workloads: list[WorkloadReport],
) -> float:

    total_weight = sum(
        workload.frequency
        for workload in workloads
    )

    if total_weight <= 0:
        return 0.0

    weighted_improvement = sum(
        workload.median_improvement_percentage
        * workload.frequency
        for workload in workloads
    )

    return round(
        weighted_improvement
        / total_weight,
        2,
    )


def build_decision_reason(
    selected_layout: str,
    workloads: list[WorkloadReport],
) -> str:

    if not workloads:
        return (
            f"Selected layout '{selected_layout}' "
            "based on available optimization evidence."
        )

    weighted_improvement = (
        calculate_workload_weighted_improvement(
            workloads
        )
    )

    return (
        f"Selected layout '{selected_layout}' "
        f"based on workload-weighted empirical "
        f"performance. The selected layout produced "
        f"{weighted_improvement:.2f}% weighted median "
        "latency improvement relative to the baseline."
    )


def save_report(
    report: OptimizationReport,
) -> None:

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report.to_dict(),
            file,
            indent=2,
        )


def print_report(
    report: OptimizationReport,
) -> None:

    print()
    print("=" * 75)
    print("LAKEOS OPTIMIZATION DECISION REPORT")
    print("=" * 75)

    print()

    print(
        f"Run ID                  : "
        f"{report.run_id}"
    )

    print(
        f"Selected layout         : "
        f"{report.selected_layout}"
    )

    print(
        f"Candidate layouts       : "
        f"{', '.join(report.candidate_layouts)}"
    )

    print()
    print("--- STORAGE ---")

    print(
        f"Baseline files          : "
        f"{report.baseline_files}"
    )

    print(
        f"Selected files          : "
        f"{report.selected_files}"
    )

    print(
        f"File-count change       : "
        f"{report.file_count_change_percentage:+.2f}%"
    )

    print(
        f"Baseline size           : "
        f"{report.baseline_size_bytes / (1024 ** 2):.2f} MB"
    )

    print(
        f"Selected size           : "
        f"{report.selected_size_bytes / (1024 ** 2):.2f} MB"
    )

    print(
        f"Storage change          : "
        f"{report.storage_change_percentage:+.2f}%"
    )

    print()
    print("--- WORKLOADS ---")

    for workload in report.workloads:

        print()
        print(
            workload.workload
        )

        print(
            f"  Frequency             : "
            f"{workload.frequency:.2f}"
        )

        print(
            f"  Baseline median       : "
            f"{workload.baseline_time_seconds:.6f}s"
        )

        print(
            f"  Selected median       : "
            f"{workload.selected_time_seconds:.6f}s"
        )

        print(
            f"  Median improvement    : "
            f"{workload.median_improvement_percentage:+.2f}%"
        )

        print(
            f"  P95 improvement       : "
            f"{workload.p95_improvement_percentage:+.2f}%"
        )

        print(
            f"  Predicted cost        : "
            f"{workload.predicted_cost:.4f}"
        )

        print(
            f"  Actual relative cost  : "
            f"{workload.actual_relative_cost:.4f}"
        )

        print(
            f"  Prediction error      : "
            f"{workload.prediction_error_percentage:+.2f}%"
        )

    print()
    print("--- DECISION ---")

    print(
        f"Weighted improvement    : "
        f"{report.workload_weighted_improvement_percentage:+.2f}%"
    )

    print(
        f"Confidence              : "
        f"{report.confidence:.2%}"
    )

    print(
        f"Reason                  : "
        f"{report.decision_reason}"
    )

    print()

    print(
        f"Report saved to         : "
        f"{REPORT_PATH}"
    )