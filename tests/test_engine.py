"""End-to-end tests: load a BPMN file and run it with Senuna."""

from pathlib import Path
from typing import Any

import pytest

from senuna import (
    BpmnParseError,
    HandlerAlreadyRegisteredError,
    HandlerNotFoundError,
    ProcessValidationError,
    Senuna,
    ServiceTaskContext,
)
from senuna.model import Process, StartEvent
from senuna.parser import BPMN_NAMESPACE

BPMN_DIR = Path(__file__).parent / "bpmn"


# The minimal example from the specification.
def test_run_hello_process() -> None:
    process_engine = Senuna()

    @process_engine.service_task("greet")
    def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
        return {"greeting": f"Hello {ctx.variables['name']}"}

    process = process_engine.load(BPMN_DIR / "hello.bpmn")
    instance = process_engine.run(process, variables={"name": "World"})

    assert instance.status == "completed"
    assert instance.variables == {"name": "World", "greeting": "Hello World"}


def test_run_a_file_with_a_diagram() -> None:
    process_engine = Senuna()
    process_engine.service_task("greet")(lambda ctx: {"greeting": "Hello"})

    process = process_engine.load(BPMN_DIR / "hello_modeler.bpmn")
    instance = process_engine.run(process)

    assert instance.status == "completed"
    assert instance.variables == {"greeting": "Hello"}


def test_a_process_can_run_many_times() -> None:
    process_engine = Senuna()

    @process_engine.service_task("greet")
    def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
        return {"greeting": f"Hello {ctx.variables['name']}"}

    process = process_engine.load(BPMN_DIR / "hello.bpmn")
    first = process_engine.run(process, variables={"name": "Ada"})
    second = process_engine.run(process, variables={"name": "Grace"})

    assert first.variables["greeting"] == "Hello Ada"
    assert second.variables["greeting"] == "Hello Grace"
    assert first.id != second.id


def test_a_failing_handler_fails_the_instance() -> None:
    process_engine = Senuna()

    @process_engine.service_task("greet")
    def greet(ctx: ServiceTaskContext) -> None:
        raise ValueError("No name")

    instance = process_engine.run(process_engine.load(BPMN_DIR / "hello.bpmn"))

    assert instance.status == "failed"
    assert instance.failure is not None
    assert instance.failure.task_id == "greet"
    assert instance.failure.error_type == "ValueError"
    assert instance.failure.message == "No name"


# --- Registering handlers -----------------------------------------------------


def test_service_task_returns_the_function_unchanged() -> None:
    process_engine = Senuna()

    def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
        return {"greeting": "Hello"}

    # The same as using @process_engine.service_task("greet") above greet.
    assert process_engine.service_task("greet")(greet) is greet


def test_a_second_handler_for_the_same_task_is_rejected() -> None:
    process_engine = Senuna()
    process_engine.service_task("greet")(lambda ctx: None)

    with pytest.raises(HandlerAlreadyRegisteredError) as exc_info:
        process_engine.service_task("greet")(lambda ctx: None)

    assert exc_info.value.task_id == "greet"


def test_engines_dont_share_handlers() -> None:
    first_engine = Senuna()
    first_engine.service_task("greet")(lambda ctx: None)
    second_engine = Senuna()

    process = second_engine.load(BPMN_DIR / "hello.bpmn")

    with pytest.raises(HandlerNotFoundError):
        second_engine.run(process)


def test_run_without_a_handler_raises_handler_not_found_error() -> None:
    process_engine = Senuna()
    process = process_engine.load(BPMN_DIR / "hello.bpmn")

    with pytest.raises(HandlerNotFoundError) as exc_info:
        process_engine.run(process)

    assert exc_info.value.task_id == "greet"


# --- Invalid files and processes ----------------------------------------------


def test_load_rejects_a_file_it_cant_read(tmp_path: Path) -> None:
    file = tmp_path / "broken.bpmn"
    file.write_text("<definitions>")

    with pytest.raises(BpmnParseError):
        Senuna().load(file)


def test_load_rejects_an_invalid_process(tmp_path: Path) -> None:
    file = tmp_path / "no_end.bpmn"
    file.write_text(
        f"""
        <bpmn:definitions xmlns:bpmn="{BPMN_NAMESPACE}">
          <bpmn:process id="no_end">
            <bpmn:startEvent id="start" />
          </bpmn:process>
        </bpmn:definitions>
        """
    )

    with pytest.raises(ProcessValidationError) as exc_info:
        Senuna().load(file)

    assert exc_info.value.problems == (
        "The process has no EndEvent",
        "StartEvent 'start' has no outgoing sequence flow",
    )


def test_run_checks_a_process_built_in_code() -> None:
    process = Process(id="only_start", flow_elements=(StartEvent(id="start"),))

    with pytest.raises(ProcessValidationError):
        Senuna().run(process)
