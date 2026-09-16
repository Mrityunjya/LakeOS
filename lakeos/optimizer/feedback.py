from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class FeedbackRecord:
    workload: str
    layout: str

    predicted_cost: float
    actual_relative_cost: float

    prediction_error: float
    error_percentage: float

    actual_time_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_feedback_record(
    workload: str,
    layout: str,
    predicted_cost: float,
    baseline_time_seconds: float,
    actual_time_seconds: float,
) -> FeedbackRecord:
    """
    Create feedback from an executed workload.

    Costs are normalized relative to the baseline:

        1.0 = same as baseline
        0.5 = twice as fast
        2.0 = twice as slow
    """

    if baseline_time_seconds <= 0:
        actual_relative_cost = 1.0
    else:
        actual_relative_cost = (
            actual_time_seconds
            / baseline_time_seconds
        )

    prediction_error = (
        actual_relative_cost
        - predicted_cost
    )

    if predicted_cost != 0:
        error_percentage = (
            prediction_error
            / predicted_cost
            * 100
        )
    else:
        error_percentage = 0.0

    return FeedbackRecord(
        workload=workload,
        layout=layout,
        predicted_cost=round(
            predicted_cost,
            4,
        ),
        actual_relative_cost=round(
            actual_relative_cost,
            4,
        ),
        prediction_error=round(
            prediction_error,
            4,
        ),
        error_percentage=round(
            error_percentage,
            2,
        ),
        actual_time_seconds=round(
            actual_time_seconds,
            6,
        ),
    )


def calculate_feedback_error(
    records: list[FeedbackRecord],
) -> float:
    """Calculate mean absolute prediction error."""

    if not records:
        return 0.0

    return sum(
        abs(record.error_percentage)
        for record in records
    ) / len(records)


def print_feedback(
    records: list[FeedbackRecord],
) -> None:

    print()
    print("=" * 75)
    print("LAKEOS ADAPTIVE FEEDBACK")
    print("=" * 75)

    for record in records:

        print()
        print(
            f"WORKLOAD: "
            f"{record.workload}"
        )

        print(
            f"LAYOUT: "
            f"{record.layout}"
        )

        print(
            f"Predicted cost : "
            f"{record.predicted_cost:.4f}"
        )

        print(
            f"Actual cost    : "
            f"{record.actual_relative_cost:.4f}"
        )

        print(
            f"Prediction err.: "
            f"{record.prediction_error:+.4f}"
        )

        print(
            f"Error          : "
            f"{record.error_percentage:+.2f}%"
        )

        print(
            f"Actual time    : "
            f"{record.actual_time_seconds:.6f}s"
        )

    print()
    print(
        f"Mean absolute error: "
        f"{calculate_feedback_error(records):.2f}%"
    )

    print("=" * 75)