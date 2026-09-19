from lakeos.metadata.catalog import (
    get_dataset,
    register_dataset,
)


def test_register_dataset(tmp_path):
    dataset_path = tmp_path / "orders"
    catalog_path = tmp_path / "catalog.json"

    year_path = (
        dataset_path
        / "year=2025"
        / "month=6"
    )

    year_path.mkdir(
        parents=True
    )

    metadata = register_dataset(
        dataset_name="test_orders",
        dataset_path=dataset_path,
        layout="month",
        file_count=1,
        total_rows=100,
        total_size_bytes=1024,
        catalog_path=catalog_path,
    )

    assert metadata.dataset_name == "test_orders"
    assert metadata.file_count == 1
    assert metadata.total_rows == 100
    assert metadata.partition_columns == [
        "month",
        "year",
    ]


def test_get_dataset(tmp_path):
    dataset_path = tmp_path / "orders"
    catalog_path = tmp_path / "catalog.json"

    dataset_path.mkdir(
        parents=True
    )

    register_dataset(
        dataset_name="lookup_test",
        dataset_path=dataset_path,
        layout="none",
        file_count=1,
        total_rows=50,
        total_size_bytes=512,
        catalog_path=catalog_path,
    )

    dataset = get_dataset(
        "lookup_test",
        catalog_path=catalog_path,
    )

    assert dataset is not None
    assert dataset.dataset_name == "lookup_test"
    assert dataset.total_rows == 50