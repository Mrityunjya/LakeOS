from dataclasses import asdict, dataclass
from typing import Any

from lakeos.optimizer.adaptive_cost_model import (
    calculate_pruning_adjustment,
    estimate_adaptive_cost,
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

    estimated_eligible_files: int
    estimated_pruned_files: int
    estimated_pruning_ratio: float

    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_partition_pruning(
    profile: WorkloadProfile,
    layout: str,
) -> dict[str, float | int]:
    """
    Estimate partition pruning for a candidate layout.

    This is a What-If calculation. No files are created
    and no benchmark is executed.

    The estimation is based on workload selectivity and
    the partition keys supported by the candidate layout.
    """

    if layout == "none":
        return {
            "eligible_files": 1,
            "pruned_files": 0,
            "pruning_ratio": 0.0,
        }

    if not profile.time_filter:
        return {
            "eligible_files": 1,
            "pruned_files": 0,
            "pruning_ratio": 0.0,
        }

    selectivity = max(
        0.0,
        min(
            profile.estimated_selectivity,
            1.0,
        ),
    )

    # --------------------------------------------------------
    # Month partitioning
    # --------------------------------------------------------

    if layout == "month":

        # A time-filtered workload can prune files
        # using year/month partition metadata.
        pruning_ratio = (
            1.0 - selectivity
        )

        # The exact number of files is unknown before
        # materialization, so we use a normalized
        # 100-file reference layout.
        reference_files = 100

        eligible_files = max(
            1,
            round(
                reference_files
                * selectivity
            ),
        )

        pruned_files = (
            reference_files
            - eligible_files
        )

        return {
            "eligible_files": eligible_files,
            "pruned_files": pruned_files,
            "pruning_ratio": pruning_ratio,
        }

    # --------------------------------------------------------
    # Month + region partitioning
    # --------------------------------------------------------

    if layout == "month_region":

        pruning_ratio = (
            1.0 - selectivity
        )

        # If the workload filters on region,
        # the region partition adds another pruning
        # opportunity.
        if (
            "region"
            in profile.filter_columns
        ):

            # Conservative additional pruning benefit.
            #
            # We intentionally do not assume perfect
            # uniformity because the dataset may be skewed.
            pruning_ratio = (
                1.0
                - (
                    selectivity
                    * 1.20
                )
            )

            pruning_ratio = max(
                0.0,
                min(
                    pruning_ratio,
                    0.99,
                ),
            )

        reference_files = 100

        eligible_files = max(
            1,
            round(
                reference_files
                * (
                    1.0
                    - pruning_ratio
                )
            ),
        )

        pruned_files = (
            reference_files
            - eligible_files
        )

        return {
            "eligible_files": eligible_files,
            "pruned_files": pruned_files,
            "pruning_ratio": pruning_ratio,
        }

    raise ValueError(
        f"Unsupported layout: {layout}"
    )


def build_rationale(
    profile: WorkloadProfile,
    layout: str,
    pruning_ratio: float,
) -> str:
    """Build an explanation for a What-If result."""

    if layout == "none":
        return (
            "Unpartitioned layout provides no "
            "partition pruning."
        )

    if not profile.time_filter:
        return (
            f"{layout} partitioning provides limited "
            "benefit because the workload has no "
            "time predicate."
        )

    if (
        layout == "month_region"
        and "region" in profile.filter_columns
    ):
        return (
            "Month and region partitioning can prune "
            "files using both workload predicates. "
            f"Estimated pruning is "
            f"{pruning_ratio:.2%}."
        )

    if layout == "month":
        return (
            "Month partitioning can prune files using "
            "the workload time predicate. "
            f"Estimated pruning is "
            f"{pruning_ratio:.2%}."
        )

    return (
        f"Candidate layout provides an estimated "
        f"{pruning_ratio:.2%} partition pruning."
    )


def evaluate_layouts(
    profile: WorkloadProfile,
) -> list[WhatIfResult]:
    """
    Evaluate all supported physical layouts for a workload.

    This is a logical What-If analysis and does not
    materialize the candidate layouts.
    """

    results: list[WhatIfResult] = []

    for layout in SUPPORTED_LAYOUTS:

        pruning = estimate_partition_pruning(
            profile,
            layout,
        )

        pruning_ratio = float(
            pruning["pruning_ratio"]
        )

        # The adaptive model receives the predicted
        # pruning benefit of this candidate.
        predicted_cost = estimate_adaptive_cost(
            profile,
            layout,
            pruning_ratio=pruning_ratio,
        )

        if layout == "none":
            pruning_score = 0.0

            balance_score = 1.0

            fragmentation_score = 1.0

        elif layout == "month":

            pruning_score = pruning_ratio

            balance_score = 1.0

            fragmentation_score = 0.85

        else:

            pruning_score = pruning_ratio

            # Month + region creates more partitions,
            # so we retain a lower balance score because
            # region distribution can be skewed.
            balance_score = 0.55

            fragmentation_score = 0.75

        rationale = build_rationale(
            profile,
            layout,
            pruning_ratio,
        )

        results.append(
            WhatIfResult(
                workload=profile.name,
                layout=layout,
                predicted_cost=round(
                    predicted_cost,
                    6,
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
                estimated_eligible_files=int(
                    pruning[
                        "eligible_files"
                    ]
                ),
                estimated_pruned_files=int(
                    pruning[
                        "pruned_files"
                    ]
                ),
                estimated_pruning_ratio=round(
                    pruning_ratio,
                    4,
                ),
                rationale=rationale,
            )
        )

    return sorted(
        results,
        key=lambda result: result.predicted_cost,
    )


def choose_layout(
    results: list[WhatIfResult],
) -> WhatIfResult:
    """Choose the lowest predicted-cost layout."""

    if not results:
        raise ValueError(
            "No What-If results available."
        )

    return min(
        results,
        key=lambda result: result.predicted_cost,
    )


def print_what_if_results(
    profile: WorkloadProfile,
    results: list[WhatIfResult],
) -> None:
    """Print What-If optimization results."""

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
            f"[{index}] {result.layout.upper()}"
        )

        print(
            f"Predicted cost        : "
            f"{result.predicted_cost:.4f}"
        )

        print(
            f"Pruning score         : "
            f"{result.pruning_score:.2%}"
        )

        print(
            f"Estimated eligible    : "
            f"{result.estimated_eligible_files}"
        )

        print(
            f"Estimated pruned      : "
            f"{result.estimated_pruned_files}"
        )

        print(
            f"Estimated pruning     : "
            f"{result.estimated_pruning_ratio:.2%}"
        )

        print(
            f"Balance score         : "
            f"{result.balance_score:.2f}"
        )

        print(
            f"Fragmentation score   : "
            f"{result.fragmentation_score:.2f}"
        )

        print(
            f"Rationale              : "
            f"{result.rationale}"
        )

    selected = choose_layout(
        results
    )

    print()
    print("-" * 75)

    print(
        f"WHAT-IF SELECTION      : "
        f"{selected.layout}"
    )

    print(
        f"Predicted cost         : "
        f"{selected.predicted_cost:.4f}"
    )

