from pathlib import Path

from lakeos.profiler.data_profiler import (
    profile_dataset,
    print_profile,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():
    profile = profile_dataset(
        DATASET_PATH
    )

    print_profile(profile)


if __name__ == "__main__":
    main()