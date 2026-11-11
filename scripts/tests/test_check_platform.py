"""Platform scheduling retains the complete suite and propagates failures."""

from __future__ import annotations

import sys
from pathlib import Path

from check_platform import commands_for
from check_platform import run_lane
from check_platform import run_lanes


def test_lanes_preserve_every_command_and_build_before_browser() -> None:
    lanes = commands_for(False)
    commands = [" ".join(command) for lane in lanes.values() for command in lane]
    for suffix in [
        "ruff check",
        "pyright",
        "mypy",
        "pytest",
        "check:client",
        "typecheck",
        "lint",
        "npm test",
        "run build",
        "test:browser",
        "services/gateway",
    ]:
        assert any(command.endswith(suffix) for command in commands)
    frontend = lanes["frontend"]
    assert frontend.index(("npm", "run", "build")) < frontend.index(("npm", "run", "test:browser"))
    assert not set(lanes["backend"]) & set(frontend)


def test_failed_lane_retains_output_and_does_not_run_dependent_steps(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    log = tmp_path / "lane.log"
    result = run_lane(
        "test",
        [
            (sys.executable, "-c", "print('failure evidence');raise SystemExit(7)"),
            (sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"),
        ],
        tmp_path,
        log,
    )
    assert result.returncode == 7
    assert len(result.steps) == 1
    assert "failure evidence" in log.read_text()
    assert not marker.exists()


def test_missing_executable_fails_lane(tmp_path: Path) -> None:
    result = run_lane("missing", [(str(tmp_path / "no-tool"),)], tmp_path, tmp_path / "log")
    assert result.returncode != 0


def test_no_tests_retains_build_and_static_checks() -> None:
    lanes = commands_for(True)
    assert ("npm", "run", "build") in lanes["frontend"]
    assert ("npm", "run", "test:browser") not in lanes["frontend"]
    assert all(command[-1] != "pytest" for command in lanes["backend"])


def test_independent_lanes_overlap_and_both_failures_survive(tmp_path: Path) -> None:
    # Each child waits for its peer to start. Sequential execution would time out.
    program = (
        "import pathlib,sys,time; "
        "pathlib.Path(sys.argv[1]).touch(); "
        "deadline=time.monotonic()+5; "
        "peer=pathlib.Path(sys.argv[2]); "
        "exec('while not peer.exists() and time.monotonic()<deadline: time.sleep(0.01)'); "
        "sys.exit(int(sys.argv[3]) if peer.exists() else 99)"
    )
    lanes = {
        "a": [(sys.executable, "-c", program, "a", "b", "7")],
        "b": [(sys.executable, "-c", program, "b", "a", "8")],
    }
    results = run_lanes(lanes, tmp_path)
    assert [result.returncode for result in results] == [7, 8]
