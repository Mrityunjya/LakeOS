from pathlib import Path

from lakeos.optimizer.recommendation_engine import (
    generate_recommendations,
)
from lakeos.optimizer.what_if import (
    evaluate_layouts,
)
from lakeos.profiler.data_profiler import (
    profile_dataset,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
)


DATASET_PATH = Path("data/sample/orders")


def test_recommendations_are_generated():
    profile = profile_dataset(DATASET_PATH)

    recommendations = generate_recommendations(
        profile
    )

    assert len(recommendations) > 0


def test_duplicate_recommendation_exists():
    profile = profile_dataset(DATASET_PATH)

    recommendations = generate_recommendations(
        profile
    )

    titles = [
        recommendation.title
        for recommendation in recommendations
    ]

    assert any(
        "Duplicate" in title
        for title in titles
    )


def test_small_file_recommendation_exists():
    profile = profile_dataset(DATASET_PATH)

    recommendations = generate_recommendations(
        profile
    )

    titles = [
        recommendation.title
        for recommendation in recommendations
    ]

    assert any(
        "Small-file" in title
        for title in titles
    )


def test_what_if_returns_all_layouts():
    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    for profile in profiles:
        results = evaluate_layouts(profile)

        layouts = {
            result.layout
            for result in results
        }

        assert layouts == {
            "none",
            "month",
            "month_region",
        }


def test_what_if_results_are_sorted_by_cost():
    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    for profile in profiles:
        results = evaluate_layouts(profile)

        costs = [
            result.predicted_cost
            for result in results
        ]

        assert costs == sorted(costs)