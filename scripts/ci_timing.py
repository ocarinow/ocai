"""Measure Actions queue/runtime distributions from read-only GitHub job data.

Use the same --limit and event for before/after windows. Runtime is workflow
completion time, not a claim that human review or every required workflow finished.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime
from typing import Any


def api(path: str) -> Any:
    """Fetch all pages as JSON through the authenticated gh client."""
    return json.loads(
        subprocess.check_output(("gh", "api", "--paginate", "--slurp", path), text=True)
    )


def percentile(values: list[float], fraction: float) -> float:
    """Return the nearest-rank percentile, or zero for no samples."""
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else 0.0


def seconds(start: str, end: str) -> float:
    """Return elapsed seconds between GitHub ISO timestamps."""
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()


def summarize(runs: list[dict[str, Any]], jobs: dict[int, list[dict[str, Any]]]) -> str:
    """Separate queue, elapsed and summed runner time; report sample size and outcomes."""
    queues: list[float] = []
    elapsed: list[float] = []
    runner: list[float] = []
    by_job: dict[str, list[float]] = {}
    successful = 0
    for run in runs:
        active = [
            job
            for job in jobs[int(run["id"])]
            if job.get("started_at")
            and job.get("completed_at")
            and job.get("conclusion") != "skipped"
        ]
        if not active:
            continue
        first = min(str(job["started_at"]) for job in active)
        last = max(str(job["completed_at"]) for job in active)
        queues.append(max(0.0, seconds(str(run["created_at"]), first)))
        elapsed.append(seconds(str(run["created_at"]), last))
        durations: list[float] = []
        for job in active:
            duration = seconds(str(job["started_at"]), str(job["completed_at"]))
            durations.append(duration)
            by_job.setdefault(str(job["name"]), []).append(duration)
        runner.append(sum(durations))
        successful += run["conclusion"] == "success"
    lines = [
        f"Measured runs: {len(elapsed)} ({successful} successful). Latest attempt per run.",
        "",
        "| Metric | Samples | Median seconds | P90 seconds |",
        "|---|---:|---:|---:|",
    ]
    for label, values in [
        ("Initial queue", queues),
        ("Workflow elapsed", elapsed),
        ("Summed runner time", runner),
        *sorted(by_job.items()),
    ]:
        lines.append(
            f"| {label} | {len(values)} | {percentile(values, 0.5):.1f} | "
            f"{percentile(values, 0.9):.1f} |"
        )
    return "\n".join(lines)


def main() -> int:
    """Print a reproducible sample of queue and execution timings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="ocarinow/ocai")
    parser.add_argument("--created", required=True, help="YYYY-MM-DD..YYYY-MM-DD")
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--branch")
    args = parser.parse_args()
    path = (
        f"repos/{args.repo}/actions/workflows/{args.workflow}/runs"
        f"?created={args.created}&event=pull_request&per_page=100"
    )
    pages = api(path)
    runs: list[dict[str, Any]] = [
        run
        for page in pages
        for run in page["workflow_runs"]
        if run["status"] == "completed" and (not args.branch or run["head_branch"] == args.branch)
    ][: args.limit]
    jobs: dict[int, list[dict[str, Any]]] = {}
    for run in runs:
        pages = api(f"repos/{args.repo}/actions/runs/{run['id']}/jobs?per_page=100")
        jobs[int(run["id"])] = [job for page in pages for job in page["jobs"]]
    print(summarize(runs, jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
