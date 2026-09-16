from dataclasses import dataclass
from typing import Any

from lakeos.optimizer.cost_model import (
    LayoutCandidate,
    estimate_layout_cost,
)
from lakeos.workload.workload_profiler import (
    WorkloadProfile,
)


SUPPORTED_LAYOUTS = [
    "none",
    "month",
    "month_region",
]


@dataclass
class WhatIfResult:
    workload: str
    layout: str

    predicted_cost: float

    pruning_score: float
    balance_score: float
    fragmentation_score: float

    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload": self.workload,
            "layout": self.layout,
            "predicted_cost": self.predicted_cost,
            "pruning_score": self.pruning_score,
            "balance_score": self.balance_score,
            "fragmentation_score": (
                self.fragmentation_score
            ),
            "rationale": self.rationale,
        }


def evaluate_layouts(
    profile: WorkloadProfile,
) -> list[WhatIfResult]:
    """
    Evaluate all supported physical layouts
    for a single workload.
    """

    results = []

    for layout in SUPPORTED_LAYOUTS:

        candidate: LayoutCandidate = (
            estimate_layout_cost(
                profile,
                layout,
            )
        )

        results.append(
            WhatIfResult(
                workload=profile.name,
                layout=candidate.name,
                predicted_cost=(
                    candidate.estimated_cost
                ),
                pruning_score=(
                    candidate.pruning_score
                ),
                balance_score=(
                    candidate.balance_score
                ),
                fragmentation_score=(
                    candidate.fragmentation_score
                ),
                rationale=candidate.rationale,
            )
        )

    return sorted(
        results,
        key=lambda result: result.predicted_cost,
    )


def choose_layout(
    profile: WorkloadProfile,
) -> WhatIfResult:
    """
    Select the lowest predicted-cost layout.
    """

    results = evaluate_layouts(
        profile
    )

    return results[0]


def print_what_if_results(
    profile: WorkloadProfile,
    results: list[WhatIfResult],
) -> None:

    print()
    print("=" * 75)
    print(
        f"WHAT-IF ANALYSIS: "
        f"{profile.name}"
    )
    print("=" * 75)

    for index, result in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"[{index}] "
            f"{result.layout}"
        )

        print(
            f"Predicted cost : "
            f"{result.predicted_cost:.4f}"
        )

        print(
            f"Pruning score  : "
            f"{result.pruning_score:.2f}"
        )

        print(
            f"Balance score  : "
            f"{result.balance_score:.2f}"
        )

        print(
            f"Fragmentation : "
            f"{result.fragmentation_score:.2f}"
        )

        print(
            f"Rationale      : "
            f"{result.rationale}"
        )

    print()
    print(
        f"SELECTED LAYOUT: "
        f"{results[0].layout}"
    )

    print("=" * 75)