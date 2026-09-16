from pathlib import Path

from lakeos.workload.workload_profiler import (
    print_workload_profiles,
    profile_workloads,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():

    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    print_workload_profiles(
        profiles
    )


if __name__ == "__main__":
    main()