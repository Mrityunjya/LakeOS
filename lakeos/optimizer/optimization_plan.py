from dataclasses import dataclass, asdict
from typing import Any

from lakeos.profiler.data_profiler import DatasetProfile
from lakeos.optimizer.recommendation_engine import (
    Recommendation,
)


@dataclass
class OptimizationAction:
    action_type: str
    priority: int
    description: str
    parameters: dict[str, Any]


@dataclass
class OptimizationPlan:
    dataset_path: str
    actions: list[OptimizationAction]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_optimization_plan(
    profile: DatasetProfile,
    recommendations: list[Recommendation],
) -> OptimizationPlan:

    actions: list[OptimizationAction] = []

    # --------------------------------------------------
    # 1. Deduplication
    # --------------------------------------------------

    if profile.duplicate_order_ids > 0:
        actions.append(
            OptimizationAction(
                action_type="deduplicate",
                priority=1,
                description=(
                    "Remove duplicate records using "
                    "order_id as the logical key."
                ),
                parameters={
                    "key": "order_id",
                    "duplicate_records": (
                        profile.duplicate_order_ids
                    ),
                },
            )
        )

    # --------------------------------------------------
    # 2. Partitioning
    # --------------------------------------------------

    has_timestamp_candidate = any(
        recommendation.category == "partitioning"
        and "Time-based" in recommendation.title
        for recommendation in recommendations
    )

    if has_timestamp_candidate:
        actions.append(
            OptimizationAction(
                action_type="repartition",
                priority=2,
                description=(
                    "Create a time-based storage layout "
                    "using the order timestamp."
                ),
                parameters={
                    "column": "order_timestamp",
                    "granularity": "month",
                },
            )
        )

    # --------------------------------------------------
    # 3. Compaction
    # --------------------------------------------------

    average_size = (
        profile.average_file_size_bytes
    )

    if average_size < 128 * 1024 * 1024:
        actions.append(
            OptimizationAction(
                action_type="compact",
                priority=3,
                description=(
                    "Compact fragmented Parquet files "
                    "into larger target files."
                ),
                parameters={
                    "current_file_count": (
                        profile.file_count
                    ),
                    "current_average_mb": round(
                        average_size
                        / (1024 * 1024),
                        2,
                    ),
                    "target_file_size_mb": 128,
                },
            )
        )

    # --------------------------------------------------
    # 4. Data quality
    # --------------------------------------------------

    for recommendation in recommendations:
        if (
            recommendation.category
            == "data_quality"
            and "Missing values" in recommendation.title
        ):
            column = recommendation.evidence[
                "column"
            ]

            actions.append(
                OptimizationAction(
                    action_type="data_quality_check",
                    priority=4,
                    description=(
                        f"Review missing values in "
                        f"{column} before publishing "
                        "the optimized dataset."
                    ),
                    parameters={
                        "column": column,
                        "null_percentage": (
                            recommendation.evidence[
                                "null_percentage"
                            ]
                        ),
                    },
                )
            )

    # --------------------------------------------------
    # Sort by execution priority
    # --------------------------------------------------

    actions.sort(
        key=lambda action: action.priority
    )

    return OptimizationPlan(
        dataset_path=profile.dataset_path,
        actions=actions,
    )


def print_optimization_plan(
    plan: OptimizationPlan,
) -> None:

    print()
    print("=" * 70)
    print("LAKEOS OPTIMIZATION PLAN")
    print("=" * 70)

    print(
        f"Dataset: {plan.dataset_path}"
    )

    print(
        f"Actions: {len(plan.actions)}"
    )

    for action in plan.actions:
        print()
        print(
            f"[Priority {action.priority}] "
            f"{action.action_type.upper()}"
        )

        print(
            f"Description: "
            f"{action.description}"
        )

        print(
            f"Parameters : "
            f"{action.parameters}"
        )

    print()
    print("=" * 70)