"""U0 scaffold: the CLI entry point must exist and respond to ``--help``."""
import subprocess
import sys


def test_cli_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "epicycles", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
