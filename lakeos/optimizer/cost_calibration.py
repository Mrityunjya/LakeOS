from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CalibrationRecord:
    workload: str
    layout: str

    predicted_cost: float

    baseline_time_seconds: float
    actual_time_seconds: float

    actual_relative_cost: float

    prediction_error: float
    error_percentage: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_relative_cost(
    baseline_time_seconds: float,
    actual_time_seconds: float,
) -> float:
    """
    Convert execution time into a relative cost.

    1.0 = same as baseline
    0.5 = half the baseline
    2.0 = twice the baseline
    """

    if baseline_time_seconds <= 0:
        return 1.0

    return (
        actual_time_seconds
        / baseline_time_seconds
    )


def calibrate_prediction(
    workload: str,
    layout: str,
    predicted_cost: float,
    baseline_time_seconds: float,
    actual_time_seconds: float,
) -> CalibrationRecord:

    actual_relative_cost = (
        calculate_relative_cost(
            baseline_time_seconds,
            actual_time_seconds,
        )
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

    return CalibrationRecord(
        workload=workload,
        layout=layout,
        predicted_cost=round(
            predicted_cost,
            4,
        ),
        baseline_time_seconds=round(
            baseline_time_seconds,
            6,
        ),
        actual_time_seconds=round(
            actual_time_seconds,
            6,
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
    )


def calculate_mean_error(
    records: list[CalibrationRecord],
) -> float:

    if not records:
        return 0.0

    return sum(
        abs(record.error_percentage)
        for record in records
    ) / len(records)


def print_calibration_results(
    records: list[CalibrationRecord],
) -> None:

    print()
    print("=" * 75)
    print("LAKEOS COST MODEL CALIBRATION")
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

    print()
    print(
        f"Mean absolute error: "
        f"{calculate_mean_error(records):.2f}%"
    )

    print("=" * 75)