import json
import math
from dataclasses import dataclass
from pathlib import Path

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

# Controls how quickly old observations lose influence.
# Higher value = slower decay.
RECENCY_DECAY = 0.90

# Maximum confidence reached with increasing observations.
CONFIDENCE_SATURATION = 10


@dataclass
class AdaptiveCorrection:
    workload: str
    layout: str
    correction_factor: float
    observations: int
    confidence: float


def load_corrections() -> dict[str, float]:
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


def load_history() -> list[dict]:
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
    """
    Convert observation count into a bounded
    confidence score between 0 and 1.

    Confidence increases with more observations
    but eventually saturates.
    """

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
    """
    Calculate exponential recency weight.

    age = 0 -> newest observation
    age = 1 -> previous observation
    age = 2 -> older observation
    """

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

    Newer observations therefore influence the model
    more strongly than older observations.

    The current observations are expected to already
    have been persisted by closed_loop.py.
    """

    history = load_history()

    grouped: dict[str, list[dict]] = {}

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

        observation_count = len(
            observations
        )

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
                actual / predicted
            )

            weight = calculate_recency_weight(
                age
            )

            weighted_sum += (
                factor * weight
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


def estimate_adaptive_cost(
    profile: WorkloadProfile,
    layout: str,
) -> float:

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

    return round(
        prediction.estimated_cost
        * correction,
        6,
    )


def print_adaptive_model(
    corrections: dict[str, float],
) -> None:

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

    observation_counts: dict[str, int] = {}

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
                "model tends to underestimate cost."
            )

        elif correction < 0.95:

            interpretation = (
                "model tends to overestimate cost."
            )

        else:

            interpretation = (
                "model is approximately calibrated."
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
