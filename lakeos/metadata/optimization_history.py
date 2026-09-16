import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_PATH = Path(
    "data/lakeos_optimization_history.json"
)


@dataclass
class OptimizationObservation:
    run_id: str
    timestamp: str
    workload: str
    layout: str

    predicted_cost: float
    actual_cost: float

    median_time_seconds: float
    p95_time_seconds: float

    baseline_time_seconds: float

    prediction_error_percentage: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_run_id() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []

    with HISTORY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def append_observations(
    observations: list[OptimizationObservation],
) -> None:

    history = load_history()

    history.extend(
        observation.to_dict()
        for observation in observations
    )

    HISTORY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with HISTORY_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history,
            file,
            indent=2,
        )


def print_history_summary() -> None:

    history = load_history()

    print()
    print("=" * 75)
    print("LAKEOS OPTIMIZATION HISTORY")
    print("=" * 75)

    if not history:
        print("No optimization history available.")
        return

    print(
        f"Observations: {len(history)}"
    )

    workloads = sorted(
        {
            item["workload"]
            for item in history
        }
    )

    layouts = sorted(
        {
            item["layout"]
            for item in history
        }
    )

    print(
        f"Workloads   : {', '.join(workloads)}"
    )

    print(
        f"Layouts     : {', '.join(layouts)}"
    )