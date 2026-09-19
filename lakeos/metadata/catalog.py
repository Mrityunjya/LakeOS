import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(
    "data/lakeos_catalog.json"
)


@dataclass
class DatasetMetadata:
    dataset_name: str
    dataset_path: str

    layout: str

    file_count: int
    total_rows: int
    total_size_bytes: int

    partition_columns: list[str]

    created_at: str
    updated_at: str

    last_optimization_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_catalog(
    catalog_path: Path = CATALOG_PATH,
) -> dict[str, Any]:

    if not catalog_path.exists():
        return {
            "datasets": {}
        }

    with catalog_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_catalog(
    catalog: dict[str, Any],
    catalog_path: Path = CATALOG_PATH,
) -> None:

    catalog_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with catalog_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            catalog,
            file,
            indent=2,
        )


def infer_partition_columns(
    dataset_path: Path,
) -> list[str]:

    partition_columns: set[str] = set()

    for path in dataset_path.rglob("*"):

        if not path.is_dir():
            continue

        for part in path.parts:

            if "=" not in part:
                continue

            key, _ = part.split(
                "=",
                1,
            )

            partition_columns.add(key)

    return sorted(
        partition_columns
    )


def register_dataset(
    dataset_name: str,
    dataset_path: str | Path,
    layout: str,
    file_count: int,
    total_rows: int,
    total_size_bytes: int,
    run_id: str | None = None,
    catalog_path: Path = CATALOG_PATH,
) -> DatasetMetadata:

    dataset_path = Path(
        dataset_path
    )

    catalog = load_catalog(
        catalog_path
    )

    datasets = catalog.setdefault(
        "datasets",
        {},
    )

    existing = datasets.get(
        dataset_name
    )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    if existing:
        created_at = existing[
            "created_at"
        ]
    else:
        created_at = now

    metadata = DatasetMetadata(
        dataset_name=dataset_name,
        dataset_path=str(
            dataset_path
        ),
        layout=layout,
        file_count=file_count,
        total_rows=total_rows,
        total_size_bytes=total_size_bytes,
        partition_columns=(
            infer_partition_columns(
                dataset_path
            )
        ),
        created_at=created_at,
        updated_at=now,
        last_optimization_run_id=run_id,
    )

    datasets[
        dataset_name
    ] = metadata.to_dict()

    save_catalog(
        catalog,
        catalog_path,
    )

    return metadata


def get_dataset(
    dataset_name: str,
    catalog_path: Path = CATALOG_PATH,
) -> DatasetMetadata | None:

    catalog = load_catalog(
        catalog_path
    )

    data = catalog.get(
        "datasets",
        {},
    ).get(
        dataset_name
    )

    if data is None:
        return None

    return DatasetMetadata(
        **data
    )


def list_datasets(
    catalog_path: Path = CATALOG_PATH,
) -> list[DatasetMetadata]:

    catalog = load_catalog(
        catalog_path
    )

    datasets = catalog.get(
        "datasets",
        {},
    )

    return [
        DatasetMetadata(**data)
        for data in datasets.values()
    ]


def print_catalog(
    catalog_path: Path = CATALOG_PATH,
) -> None:

    datasets = list_datasets(
        catalog_path
    )

    print()
    print("=" * 80)
    print("LAKEOS DATASET CATALOG")
    print("=" * 80)

    if not datasets:
        print(
            "No datasets registered."
        )
        return

    print(
        f"Datasets: {len(datasets)}"
    )

    for dataset in datasets:

        print()

        print(
            f"Dataset : "
            f"{dataset.dataset_name}"
        )

        print(
            f"Path    : "
            f"{dataset.dataset_path}"
        )

        print(
            f"Layout  : "
            f"{dataset.layout}"
        )

        print(
            f"Files   : "
            f"{dataset.file_count:,}"
        )

        print(
            f"Rows    : "
            f"{dataset.total_rows:,}"
        )

        print(
            f"Size    : "
            f"{dataset.total_size_bytes / (1024 ** 2):.2f} MB"
        )

        partitions = (
            ", ".join(
                dataset.partition_columns
            )
            if dataset.partition_columns
            else "None"
        )

        print(
            f"Partitions: "
            f"{partitions}"
        )

        print(
            f"Last run: "
            f"{dataset.last_optimization_run_id or 'None'}"
        )