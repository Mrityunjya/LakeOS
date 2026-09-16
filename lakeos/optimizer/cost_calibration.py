from dataclasses import dataclass
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
        return {
            "workload": self.workload,
            "layout": self.layout,
            "predicted_cost": self.predicted_cost,
            "baseline_time_seconds": (
                self.baseline_time_seconds
            ),
            "actual_time_seconds": (
                self.actual_time_seconds
            ),
            "actual_relative_cost": (
                self.actual_relative_cost
            ),
            "prediction_error": (
                self.prediction_error
            ),
            "error_percentage": (
                self.error_percentage
            ),
        }


# ============================================================
# NORMALIZATION
# ============================================================

def calculate_relative_cost(
    baseline_time_seconds: float,
    actual_time_seconds: float,
) -> float:
    """
    Normalize an execution time against the baseline
    execution time for the same workload.

    A value of:

        1.0  = same cost as baseline
        0.5  = half the baseline cost
        0.1  = one tenth of baseline cost
    """

    if baseline_time_seconds <= 0:
        return 1.0

    return (
        actual_time_seconds
        / baseline_time_seconds
    )


# ============================================================
# CALIBRATION
# ============================================================

def calibrate_prediction(
    workload: str,
    layout: str,
    predicted_cost: float,
    baseline_time_seconds: float,
    actual_time_seconds: float,
) -> CalibrationRecord:
    """
    Compare the model's predicted relative cost with
    the measured relative execution cost.
    """

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

    if actual_relative_cost > 0:

        error_percentage = (
            abs(prediction_error)
            / actual_relative_cost
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


# ============================================================
# SUMMARY
# ============================================================

def calculate_mean_error(
    records: list[CalibrationRecord],
) -> float:
    """
    Calculate mean absolute percentage error
    across calibration records.
    """

    if not records:
        return 0.0

    return sum(
        record.error_percentage
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
            f"Layout             : "
            f"{record.layout}"
        )

        print(
            f"Predicted cost     : "
            f"{record.predicted_cost:.4f}"
        )

        print(
            f"Baseline time      : "
            f"{record.baseline_time_seconds:.6f}s"
        )

        print(
            f"Actual time        : "
            f"{record.actual_time_seconds:.6f}s"
        )

        print(
            f"Actual relative    : "
            f"{record.actual_relative_cost:.4f}"
        )

        print(
            f"Prediction error   : "
            f"{record.prediction_error:.4f}"
        )

        print(
            f"Error percentage   : "
            f"{record.error_percentage:.2f}%"
        )

    mean_error = calculate_mean_error(
        records
    )

    print()
    print("-" * 75)

    print(
        f"Mean absolute "
        f"percentage error: "
        f"{mean_error:.2f}%"
    )

    print("=" * 75)