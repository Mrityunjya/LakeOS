import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lakeos.optimizer.cost_model import (
    estimate_layout_cost,
)
from lakeos.workload.workload_profiler import (
    WorkloadProfile,
)


MODEL_PATH = Path(
    "data/lakeos_cost_model.json"
)

HISTORY_PATH = Path(
    "data/lakeos_optimization_history.json"
)

RECENCY_DECAY = 0.90
CONFIDENCE_SATURATION = 10


@dataclass
class AdaptiveCorrection:
    workload: str
    layout: str
    correction_factor: float
    observations: int
    confidence: float


def load_corrections() -> dict[str, float]:
    """Load persisted adaptive correction factors."""

    if not MODEL_PATH.exists():
        return {}

    with MODEL_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return {
        key: float(value)
        for key, value in data.items()
    }


def save_corrections(
    corrections: dict[str, float],
) -> None:
    """Persist adaptive correction factors."""

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MODEL_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            corrections,
            file,
            indent=2,
        )


def load_history() -> list[dict[str, Any]]:
    """Load persisted optimization history."""

    if not HISTORY_PATH.exists():
        return []

    with HISTORY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def correction_key(
    workload: str,
    layout: str,
) -> str:
    return f"{workload}:{layout}"


def calculate_confidence(
    observation_count: int,
) -> float:
    """Convert observation count into bounded confidence."""

    if observation_count <= 0:
        return 0.0

    confidence = (
        1
        - math.exp(
            -observation_count
            / CONFIDENCE_SATURATION
        )
    )

    return round(
        confidence,
        4,
    )


def calculate_recency_weight(
    age: int,
) -> float:
    """Return exponentially decayed historical weight."""

    return RECENCY_DECAY ** age


def update_corrections(
    records,
) -> dict[str, float]:
    """
    Recalculate adaptive correction factors using
    the complete persisted optimization history.

    correction_factor =
        actual_relative_cost / predicted_cost

    Historical observations are weighted by recency.

    The current observations are expected to already
    have been persisted by closed_loop.py.
    """

    history = load_history()

    grouped: dict[
        str,
        list[dict[str, float]],
    ] = {}

    for record in history:

        predicted = float(
            record.get(
                "predicted_cost",
                0.0,
            )
        )

        actual = float(
            record.get(
                "actual_cost",
                1.0,
            )
        )

        if predicted <= 0:
            continue

        key = correction_key(
            record["workload"],
            record["layout"],
        )

        grouped.setdefault(
            key,
            [],
        ).append(
            {
                "predicted": predicted,
                "actual": actual,
            }
        )

    corrections: dict[str, float] = {}

    for key, observations in grouped.items():

        if not observations:
            continue

        weighted_sum = 0.0
        total_weight = 0.0

        for age, observation in enumerate(
            reversed(observations)
        ):

            predicted = observation[
                "predicted"
            ]

            actual = observation[
                "actual"
            ]

            factor = (
                actual
                / predicted
            )

            weight = calculate_recency_weight(
                age
            )

            weighted_sum += (
                factor
                * weight
            )

            total_weight += weight

        if total_weight == 0:
            continue

        correction = (
            weighted_sum
            / total_weight
        )

        corrections[key] = round(
            correction,
            6,
        )

    save_corrections(
        corrections
    )

    return corrections


def calculate_pruning_adjustment(
    pruning_ratio: float,
    workload_type: str,
) -> float:
    """
    Estimate the performance benefit of partition pruning.

    This is intentionally conservative.

    A high pruning ratio should reduce predicted cost
    for workloads that actually benefit from filtering.

    Full-scan aggregations are not rewarded simply because
    a layout happens to be partitioned.
    """

    pruning_ratio = max(
        0.0,
        min(
            pruning_ratio,
            1.0,
        ),
    )

    if workload_type == "full_scan_aggregation":
        return 1.0

    if pruning_ratio <= 0:
        return 1.0

    # Conservative nonlinear adjustment.
    #
    # Example:
    # 50% pruning -> ~0.82
    # 90% pruning -> ~0.66
    # 98% pruning -> ~0.62
    #
    # This prevents the model from assuming that
    # eliminating 90% of files means a 90% latency
    # reduction.
    adjustment = (
        1.0
        - 0.40
        * math.sqrt(
            pruning_ratio
        )
    )

    return round(
        max(
            0.60,
            adjustment,
        ),
        6,
    )


def estimate_adaptive_cost(
    profile: WorkloadProfile,
    layout: str,
    pruning_ratio: float = 0.0,
) -> float:
    """
    Estimate workload cost using:

        theoretical cost
            × adaptive historical correction
            × pruning adjustment

    pruning_ratio should come from benchmarked
    Hive-style partition metadata.

    If pruning_ratio is unavailable, the adjustment
    defaults to 1.0, preserving previous behavior.
    """

    prediction = estimate_layout_cost(
        profile,
        layout,
    )

    corrections = load_corrections()

    key = correction_key(
        profile.name,
        layout,
    )

    correction = corrections.get(
        key,
        1.0,
    )

    pruning_adjustment = (
        calculate_pruning_adjustment(
            pruning_ratio,
            profile.workload_type,
        )
    )

    adaptive_cost = (
        prediction.estimated_cost
        * correction
        * pruning_adjustment
    )

    return round(
        adaptive_cost,
        6,
    )


def print_adaptive_model(
    corrections: dict[str, float],
) -> None:
    """Print persisted adaptive model state."""

    print()
    print("=" * 75)
    print(
        "LAKEOS RECENCY-WEIGHTED "
        "ADAPTIVE COST MODEL"
    )
    print("=" * 75)

    if not corrections:
        print(
            "No historical corrections available."
        )
        return

    history = load_history()

    observation_counts: dict[
        str,
        int,
    ] = {}

    for record in history:

        key = correction_key(
            record["workload"],
            record["layout"],
        )

        observation_counts[key] = (
            observation_counts.get(
                key,
                0,
            )
            + 1
        )

    for key, correction in sorted(
        corrections.items()
    ):

        observations = observation_counts.get(
            key,
            0,
        )

        confidence = calculate_confidence(
            observations
        )

        if correction > 1.05:

            interpretation = (
                "model tends to "
                "underestimate cost."
            )

        elif correction < 0.95:

            interpretation = (
                "model tends to "
                "overestimate cost."
            )

        else:

            interpretation = (
                "model is approximately "
                "calibrated."
            )

        print()
        print(key)

        print(
            f"Correction factor: "
            f"{correction:.4f}"
        )

        print(
            f"Observations: "
            f"{observations}"
        )

        print(
            f"Confidence: "
            f"{confidence:.2%}"
        )

        print(
            f"Interpretation: "
            f"{interpretation}"
        )
