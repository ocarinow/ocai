"""Timings distinguish parallel runner usage from time spent waiting."""

from typing import Any

from ci_timing import summarize


def test_parallel_jobs_are_not_reported_as_elapsed_wait() -> None:
    runs: list[dict[str, Any]] = [
        {"id": 1, "created_at": "2026-11-10T00:00:00Z", "conclusion": "success"}
    ]
    jobs: dict[int, list[dict[str, Any]]] = {
        1: [
            {
                "name": name,
                "started_at": "2026-11-10T00:00:10Z",
                "completed_at": "2026-11-10T00:01:10Z",
                "conclusion": "success",
            }
            for name in ["python", "platform"]
        ]
    }
    report = summarize(runs, jobs)
    assert "| Initial queue | 1 | 10.0 | 10.0 |" in report
    assert "| Workflow elapsed | 1 | 70.0 | 70.0 |" in report
    assert "| Summed runner time | 1 | 120.0 | 120.0 |" in report
