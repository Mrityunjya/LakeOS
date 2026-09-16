from dataclasses import dataclass
from typing import Any

from lakeos.workload.workload_profiler import (
    WorkloadProfile,
)


@dataclass
class LayoutCandidate:
    name: str
    description: str

    estimated_cost: float

    pruning_score: float
    balance_score: float
    fragmentation_score: float

    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "estimated_cost": self.estimated_cost,
            "pruning_score": self.pruning_score,
            "balance_score": self.balance_score,
            "fragmentation_score": self.fragmentation_score,
            "rationale": self.rationale,
        }


# ============================================================
# COST MODEL
# ============================================================

def estimate_layout_cost(
    workload: WorkloadProfile,
    layout: str,
) -> LayoutCandidate:
    """
    Estimate the relative cost of executing a workload
    under a particular physical data layout.

    Lower estimated cost is better.

    This is intentionally a lightweight analytical model.
    Later versions can incorporate real query telemetry,
    bytes scanned, file statistics, and historical benchmarks.
    """

    rationale: list[str] = []

    pruning_score = 0.0
    balance_score = 1.0
    fragmentation_score = 1.0

    # --------------------------------------------------------
    # No partitioning
    # --------------------------------------------------------

    if layout == "none":

        pruning_score = 0.0

        if workload.time_filter:

            rationale.append(
                "Time-filtered workload cannot "
                "benefit from partition pruning."
            )

        if workload.aggregation:

            rationale.append(
                "Full-data aggregation is compatible "
                "with a compact unpartitioned layout."
            )

        cost = 1.0

    # --------------------------------------------------------
    # Monthly partitioning
    # --------------------------------------------------------

    elif layout == "month":

        if workload.time_filter:

            # Higher selectivity means greater benefit
            # from partition pruning.
            pruning_score = (
                1.0
                - workload.estimated_selectivity
            )

            rationale.append(
                "Workload contains a time predicate."
            )

            rationale.append(
                "Monthly partitioning can eliminate "
                "irrelevant time partitions."
            )

        else:

            pruning_score = 0.0

            rationale.append(
                "Workload does not contain a time "
                "predicate, so partition pruning "
                "provides limited benefit."
            )

        cost = (
            1.0
            - (
                pruning_score
                * 0.75
            )
        )

    # --------------------------------------------------------
    # Month + region
    # --------------------------------------------------------

    elif layout == "month_region":

        if workload.time_filter:

            pruning_score = (
                1.0
                - workload.estimated_selectivity
            )

            rationale.append(
                "Time filtering benefits from "
                "monthly partition pruning."
            )

        if "region" in workload.filter_columns:

            pruning_score = min(
                pruning_score + 0.20,
                1.0,
            )

            rationale.append(
                "Region filtering could further "
                "reduce the candidate data."
            )

        else:

            rationale.append(
                "Workload does not filter by region."
            )

        # Region is known to be skewed in this dataset.
        balance_score = 0.55

        rationale.append(
            "Region has significant data skew, "
            "reducing partition balance."
        )

        fragmentation_score = 0.75

        rationale.append(
            "Composite partitioning creates more "
            "physical partitions and increases "
            "fragmentation risk."
        )

        cost = (
            1.0
            - (
                pruning_score
                * 0.80
            )
            + (
                (1.0 - balance_score)
                * 0.15
            )
            + (
                (1.0 - fragmentation_score)
                * 0.10
            )
        )

    else:

        raise ValueError(
            f"Unknown layout: {layout}"
        )

    return LayoutCandidate(
        name=layout,
        description=(
            f"Candidate physical layout: {layout}"
        ),
        estimated_cost=round(
            cost,
            4,
        ),
        pruning_score=round(
            pruning_score,
            4,
        ),
        balance_score=round(
            balance_score,
            4,
        ),
        fragmentation_score=round(
            fragmentation_score,
            4,
        ),
        rationale=rationale,
    )


# ============================================================
# CANDIDATE EVALUATION
# ============================================================

def evaluate_candidates(
    workload: WorkloadProfile,
) -> list[LayoutCandidate]:
    """
    Evaluate all supported physical layouts.
    """

    layouts = [
        "none",
        "month",
        "month_region",
    ]

    candidates = [
        estimate_layout_cost(
            workload,
            layout,
        )
        for layout in layouts
    ]

    return sorted(
        candidates,
        key=lambda candidate:
            candidate.estimated_cost,
    )


# ============================================================
# WORKLOAD-AWARE DECISION
# ============================================================

def choose_layout(
    workload: WorkloadProfile,
) -> LayoutCandidate:
    """
    Select the lowest-cost layout for a workload.
    """

    candidates = evaluate_candidates(
        workload
    )

    return candidates[0]


# ============================================================
# HUMAN-READABLE OUTPUT
# ============================================================

def print_cost_model(
    workload: WorkloadProfile,
    candidates: list[LayoutCandidate],
) -> None:

    print()
    print("=" * 75)

    print(
        f"COST MODEL: "
        f"{workload.name}"
    )

    print("=" * 75)

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):

        print()

        print(
            f"[{rank}] "
            f"{candidate.name}"
        )

        print(
            f"Estimated cost : "
            f"{candidate.estimated_cost:.4f}"
        )

        print(
            f"Pruning score  : "
            f"{candidate.pruning_score:.2f}"
        )

        print(
            f"Balance score  : "
            f"{candidate.balance_score:.2f}"
        )

        print(
            f"Fragmentation  : "
            f"{candidate.fragmentation_score:.2f}"
        )

        for reason in candidate.rationale:

            print(
                f"  - {reason}"
            )

    print()

    selected = candidates[0]

    print(
        f"SELECTED LAYOUT: "
        f"{selected.name}"
    )

    print("=" * 75)