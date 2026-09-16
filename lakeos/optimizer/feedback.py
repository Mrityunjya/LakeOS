from dataclasses import dataclass
from typing import Any


@dataclass
class FeedbackRecord:
    workload: str
    layout: str

    predicted_cost: float
    actual_time_seconds: float

    prediction_error: float
    error_percentage: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload": self.workload,
            "layout": self.layout,
            "predicted_cost": self.predicted_cost,
            "actual_time_seconds": self.actual_time_seconds,
            "prediction_error": self.prediction_error,
            "error_percentage": self.error_percentage,
        }


def create_feedback_record(
    workload: str,
    layout: str,
    predicted_cost: float,
    actual_time_seconds: float,
) -> FeedbackRecord:
    """
    Compare the optimizer's predicted cost with
    the measured execution time.

    The values are normalized relative to the
    workload's actual measurement.
    """

    prediction_error = (
        actual_time_seconds
        - predicted_cost
    )

    if actual_time_seconds > 0:

        error_percentage = (
            abs(prediction_error)
            / actual_time_seconds
            * 100
        )

    else:

        error_percentage = 0.0

    return FeedbackRecord(
        workload=workload,
        layout=layout,

        predicted_cost=round(
            predicted_cost,
            6,
        ),

        actual_time_seconds=round(
            actual_time_seconds,
            6,
        ),

        prediction_error=round(
            prediction_error,
            6,
        ),

        error_percentage=round(
            error_percentage,
            2,
        ),
    )


def print_feedback(
    records: list[FeedbackRecord],
) -> None:

    print()
    print("=" * 75)
    print("LAKEOS OPTIMIZER FEEDBACK")
    print("=" * 75)

    for record in records:

        print()

        print(
            f"Workload : "
            f"{record.workload}"
        )

        print(
            f"Layout   : "
            f"{record.layout}"
        )

        print(
            f"Predicted: "
            f"{record.predicted_cost:.6f}"
        )

        print(
            f"Actual   : "
            f"{record.actual_time_seconds:.6f}s"
        )

        print(
            f"Error    : "
            f"{record.error_percentage:.2f}%"
        )

    print()
    print("=" * 75)