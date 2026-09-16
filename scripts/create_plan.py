from pathlib import Path

from lakeos.optimizer.optimization_plan import (
    create_optimization_plan,
    print_optimization_plan,
)
from lakeos.optimizer.recommendation_engine import (
    generate_recommendations,
)
from lakeos.profiler.data_profiler import (
    profile_dataset,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():

    print("Building LAKEOS optimization plan...")

    profile = profile_dataset(
        DATASET_PATH
    )

    recommendations = (
        generate_recommendations(
            profile
        )
    )

    plan = create_optimization_plan(
        profile,
        recommendations,
    )

    print_optimization_plan(plan)


if __name__ == "__main__":
    main()