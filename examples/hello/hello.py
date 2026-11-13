"""The minimal senuna example: start -> greet -> end.

Run it from the repository root:

    uv run python examples/hello/hello.py
"""

from pathlib import Path
from typing import Any

from senuna import Senuna, ServiceTaskContext

process_engine = Senuna()


# The handler for <serviceTask id="greet"> in hello.bpmn.
@process_engine.service_task("greet")
def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
    return {"greeting": f"Hello {ctx.variables['name']}"}


# __file__ is the path of this script, so hello.bpmn is found next to it
# wherever the script is started from.
process = process_engine.load(Path(__file__).parent / "hello.bpmn")
instance = process_engine.run(process, variables={"name": "World"})

print(instance.status, instance.variables["greeting"])  # completed Hello World
