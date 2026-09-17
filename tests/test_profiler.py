from pathlib import Path

from lakeos.profiler.data_profiler import (
    profile_dataset,
)


DATASET_PATH = Path("data/sample/orders")


def test_profile_detects_expected_file_count():
    profile = profile_dataset(DATASET_PATH)

    assert profile.file_count == 101


def test_profile_detects_expected_row_count():
    profile = profile_dataset(DATASET_PATH)

    assert profile.total_rows == 1_005_000


def test_profile_detects_duplicates():
    profile = profile_dataset(DATASET_PATH)

    assert profile.duplicate_order_ids == 5_000


def test_profile_detects_region_skew():
    profile = profile_dataset(DATASET_PATH)

    assert (
        profile.region_distribution["Chennai"]
        > 400_000
    )

    assert (
        profile.region_distribution["Hyderabad"]
        < 100_000
    )


def test_profile_detects_payment_nulls():
    profile = profile_dataset(DATASET_PATH)

    payment_column = next(
        column
        for column in profile.columns
        if column.name == "payment_method"
    )

    assert payment_column.null_count > 0
    assert payment_column.null_percentage > 0