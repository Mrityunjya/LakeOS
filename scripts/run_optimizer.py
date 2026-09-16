from pathlib import Path

from lakeos.optimizer.recommendation_engine import (
    generate_recommendations,
    print_recommendations,
)
from lakeos.profiler.data_profiler import (
    profile_dataset,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():

    print("Running LAKEOS optimizer...")

    profile = profile_dataset(
        DATASET_PATH
    )

    recommendations = (
        generate_recommendations(
            profile
        )
    )

    print_recommendations(
        recommendations
    )


if __name__ == "__main__":
    main()