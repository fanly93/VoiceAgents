import subprocess
import sys


def test_cli_validates_sample_dataset() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_call_evaluations.py", "data/call-evaluations/sample.json"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Validation passed" in result.stdout

