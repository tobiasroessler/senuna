"""End-to-end test for the minimal example: start event -> service task -> end event."""

from pathlib import Path
from typing import Any

import pytest

BPMN_DIR = Path(__file__).parent / "bpmn"


@pytest.mark.xfail(raises=ImportError, reason="Senuna is not implemented yet (step 6)")
def test_run_hello_process() -> None:
    # Imported here so the other tests still run while Senuna doesn't exist.
    # Move it to the top of the file when the xfail marker is removed.
    from senuna import Senuna

    process_engine = Senuna()

    @process_engine.service_task("greet")
    def greet(ctx: Any) -> dict[str, Any]:
        return {"greeting": f"Hello {ctx.variables['name']}"}

    process = process_engine.load(BPMN_DIR / "hello.bpmn")
    instance = process_engine.run(process, variables={"name": "World"})

    assert instance.status == "completed"
    assert instance.variables == {"name": "World", "greeting": "Hello World"}
