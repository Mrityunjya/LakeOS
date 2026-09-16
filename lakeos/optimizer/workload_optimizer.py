from dataclasses import dataclass
from typing import Any

from lakeos.optimizer.cost_model import (
    LayoutCandidate,
    estimate_layout_cost,
)
from lakeos.workload.workload_profiler import (
    WorkloadProfile,
)


@dataclass
class WorkloadWeight:
    workload: WorkloadProfile
    frequency: float


@dataclass
class LayoutEvaluation:
    layout: str
    total_cost: float
    workload_costs: dict[str, float]
    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout": self.layout,
            "total_cost": self.total_cost,
            "workload_costs": self.workload_costs,
            "rationale": self.rationale,
        }


# ============================================================
# DEFAULT WORKLOAD FREQUENCIES
# ============================================================

DEFAULT_FREQUENCIES = {
    "monthly_orders": 0.50,
    "regional_monthly_orders": 0.35,
    "revenue_by_region": 0.15,
}


# ============================================================
# EVALUATE ONE LAYOUT ACROSS ALL WORKLOADS
# ============================================================

def evaluate_layout(
    layout: str,
    workloads: list[WorkloadWeight],
) -> LayoutEvaluation:
    """
    Calculate the weighted cost of one physical layout
    across the complete workload.
    """

    total_cost = 0.0

    workload_costs: dict[str, float] = {}

    rationale: list[str] = []

    for workload_weight in workloads:

        candidate = estimate_layout_cost(
            workload_weight.workload,
            layout,
        )

        weighted_cost = (
            candidate.estimated_cost
            * workload_weight.frequency
        )

        total_cost += weighted_cost

        workload_costs[
            workload_weight.workload.name
        ] = round(
            weighted_cost,
            4,
        )

    if layout == "month":

        rationale.append(
            "Strong fit for the time-filtered "
            "workload."
        )

        rationale.append(
            "Also supports regional queries "
            "through post-partition filtering."
        )

    elif layout == "none":

        rationale.append(
            "Simple physical layout with "
            "minimal partition management."
        )

        rationale.append(
            "Suitable for full-data aggregations."
        )

    elif layout == "month_region":

        rationale.append(
            "Can exploit both time and region "
            "predicates."
        )

        rationale.append(
            "Introduces additional partitions "
            "and skew risk."
        )

    return LayoutEvaluation(
        layout=layout,
        total_cost=round(
            total_cost,
            4,
        ),
        workload_costs=workload_costs,
        rationale=rationale,
    )


# ============================================================
# GLOBAL WORKLOAD OPTIMIZATION
# ============================================================

def optimize_for_workload(
    profiles: list[WorkloadProfile],
    frequencies: dict[str, float] | None = None,
) -> list[LayoutEvaluation]:
    """
    Evaluate physical layouts against the complete
    workload distribution.

    Lower total cost is better.
    """

    if frequencies is None:

        frequencies = DEFAULT_FREQUENCIES

    weighted_workloads: list[
        WorkloadWeight
    ] = []

    for profile in profiles:

        frequency = frequencies.get(
            profile.name,
            0.0,
        )

        weighted_workloads.append(
            WorkloadWeight(
                workload=profile,
                frequency=frequency,
            )
        )

    layouts = [
        "none",
        "month",
        "month_region",
    ]

    evaluations = [
        evaluate_layout(
            layout,
            weighted_workloads,
        )
        for layout in layouts
    ]

    return sorted(
        evaluations,
        key=lambda evaluation:
            evaluation.total_cost,
    )


# ============================================================
# OUTPUT
# ============================================================

def print_workload_optimization(
    evaluations: list[LayoutEvaluation],
) -> None:

    print()
    print("=" * 75)
    print("LAKEOS GLOBAL WORKLOAD OPTIMIZER")
    print("=" * 75)

    for rank, evaluation in enumerate(
        evaluations,
        start=1,
    ):

        print()

        print(
            f"[{rank}] "
            f"{evaluation.layout}"
        )

        print(
            f"Total weighted cost: "
            f"{evaluation.total_cost:.4f}"
        )

        print(
            "Workload contributions:"
        )

        for (
            workload,
            cost,
        ) in evaluation.workload_costs.items():

            print(
                f"  {workload:30} "
                f"{cost:.4f}"
            )

        for reason in evaluation.rationale:

            print(
                f"  - {reason}"
            )

    print()

    selected = evaluations[0]

    print(
        f"SELECTED GLOBAL LAYOUT: "
        f"{selected.layout}"
    )

    print(
        f"GLOBAL COST: "
        f"{selected.total_cost:.4f}"
    )

    print("=" * 75)