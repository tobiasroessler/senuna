"""The scripts in examples/ run and print what the README shows."""

import runpy
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# runpy.run_path() runs a Python file like "python hello.py" would, but
# inside this test. capsys is a built-in pytest fixture that captures what
# the code prints; readouterr().out is the printed text.
def test_hello_example(capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(EXAMPLES_DIR / "hello" / "hello.py"), run_name="__main__")

    assert capsys.readouterr().out == "completed Hello World\n"
