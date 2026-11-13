# senuna

[![CI](https://github.com/tobiasroessler/senuna/actions/workflows/ci.yml/badge.svg)](https://github.com/tobiasroessler/senuna/actions/workflows/ci.yml)

Senuna is a lightweight BPMN 2.0 workflow engine for Python.

- **Embedded:** a library that runs inside your Python application, not a separate server.
- **No dependencies:** only the Python standard library.
- **Close to the standard:** names follow the BPMN 2.0 specification (`Process`, `ServiceTask`, ...).

> **Status: early development (v0.1).** Processes can use start events,
> service tasks, end events and sequence flows, so they run in a straight
> line from start to end. Gateways, user tasks and persistence come later.

## Installation

senuna isn't on PyPI yet. Install it from GitHub (Python 3.12 or newer):

```bash
uv add git+https://github.com/tobiasroessler/senuna
```

```bash
pip install git+https://github.com/tobiasroessler/senuna
```

## Example

A process with one service task, drawn in a BPMN modeler and saved as
`hello.bpmn`:

```
(Name given) --> [Greet] --> (Greeted)
```

The Python code links a function to the service task and runs the process:

```python
from typing import Any

from senuna import Senuna, ServiceTaskContext

process_engine = Senuna()


@process_engine.service_task("greet")
def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
    return {"greeting": f"Hello {ctx.variables['name']}"}


process = process_engine.load("hello.bpmn")
instance = process_engine.run(process, variables={"name": "World"})

print(instance.status, instance.variables["greeting"])  # completed Hello World
```

- `service_task("greet")` makes the function the handler of
  `<bpmn:serviceTask id="greet">`.
- `load()` reads the BPMN file and checks that senuna can run it.
- `run()` runs the process from start to end and returns the process
  instance.
- A handler gets `ctx` with the instance's `variables` (read-only),
  `instance_id` and `task_id`. It returns a dict, which is merged into the
  variables, or `None`.

The complete example is in [`examples/hello`](examples/hello). Run it from
the repository root:

```bash
uv run python examples/hello/hello.py
```

## Drawing a process in Camunda Modeler

Any BPMN 2.0 modeler works. In [Camunda Modeler](https://camunda.com/download/modeler/):

1. Create a new BPMN diagram.
2. Draw a start event, a task and an end event, connected by arrows.
3. Turn the task into a service task: select it, click the wrench icon and
   choose **Service Task**.
4. In the properties panel, set the task's **ID** to the name used in the
   code, e.g. `greet` for `@process_engine.service_task("greet")`.
5. Save the file.

senuna skips the diagram layout, documentation and vendor settings. It
rejects elements it can't run yet, such as gateways, and lists all of them
in one error.

## When something goes wrong

- **The BPMN file or the process has a problem:** `load()` raises
  `BpmnParseError` or `ProcessValidationError`. Both list every problem
  found, so the file can be fixed in one go.
- **A service task has no handler:** `run()` raises `HandlerNotFoundError`
  before anything runs.
- **A handler raises an exception:** `run()` doesn't raise. The instance
  has the status `failed`, and `instance.failure` says what went wrong:

  ```python
  instance = process_engine.run(process, variables={})  # no "name"
  print(instance.status)  # failed
  print(instance.failure.task_id)  # greet
  print(instance.failure.error_type)  # KeyError
  ```

All exceptions derive from `SenunaError`.

## Development

```bash
uv sync               # create .venv and install everything
uv run pytest         # run the tests
uv run ruff check     # lint
uv run ruff format    # format
uv run mypy           # type check
```

GitHub Actions runs the same checks on every push to `main` and on every
pull request, with the tests on Python 3.12, 3.13 and 3.14
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## License

MIT, see [LICENSE](LICENSE).
