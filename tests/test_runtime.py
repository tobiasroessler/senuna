"""Tests for running processes with senuna.runtime."""

from typing import Any

import pytest

from senuna import HandlerNotFoundError
from senuna.model import EndEvent, Process, SequenceFlow, ServiceTask, StartEvent
from senuna.runtime import InstanceStatus, ServiceTaskContext, Token, run


def greet(ctx: ServiceTaskContext) -> dict[str, Any]:
    return {"greeting": f"Hello {ctx.variables['name']}"}


@pytest.fixture
def chain_process() -> Process:
    """start -> first -> second -> end."""
    return Process(
        id="chain",
        flow_elements=(
            StartEvent(id="start"),
            SequenceFlow(id="flow1", source_ref="start", target_ref="first"),
            ServiceTask(id="first"),
            SequenceFlow(id="flow2", source_ref="first", target_ref="second"),
            ServiceTask(id="second"),
            SequenceFlow(id="flow3", source_ref="second", target_ref="end"),
            EndEvent(id="end"),
        ),
    )


# --- Completing ---------------------------------------------------------------


def test_hello_process_completes(hello_process: Process) -> None:
    instance = run(hello_process, {"greet": greet}, {"name": "World"})

    assert instance.status == InstanceStatus.COMPLETED
    assert instance.process_id == "hello"
    assert instance.variables == {"name": "World", "greeting": "Hello World"}
    assert instance.tokens == []
    assert instance.failure is None


def test_status_compares_equal_to_its_string(hello_process: Process) -> None:
    instance = run(hello_process, {"greet": greet}, {"name": "World"})

    assert instance.status == "completed"


def test_variables_are_optional(hello_process: Process) -> None:
    instance = run(hello_process, {"greet": lambda ctx: None})

    assert instance.status == "completed"
    assert instance.variables == {}


def test_callers_variables_are_not_changed(hello_process: Process) -> None:
    variables = {"name": "World"}

    run(hello_process, {"greet": greet}, variables)

    assert variables == {"name": "World"}


def test_service_tasks_run_in_order(chain_process: Process) -> None:
    calls: list[str] = []

    def first(ctx: ServiceTaskContext) -> dict[str, Any]:
        calls.append(ctx.task_id)
        return {"count": 1}

    def second(ctx: ServiceTaskContext) -> dict[str, Any]:
        calls.append(ctx.task_id)
        return {"count": ctx.variables["count"] + 1}  # sees what first returned

    instance = run(chain_process, {"first": first, "second": second})

    assert calls == ["first", "second"]
    assert instance.variables == {"count": 2}


def test_returned_variables_overwrite_existing_ones(hello_process: Process) -> None:
    instance = run(hello_process, {"greet": lambda ctx: {"name": "Ada"}}, {"name": "x"})

    assert instance.variables == {"name": "Ada"}


# --- Handler context ----------------------------------------------------------


def test_handler_receives_the_context(hello_process: Process) -> None:
    received: list[ServiceTaskContext] = []

    def handler(ctx: ServiceTaskContext) -> None:
        received.append(ctx)

    instance = run(hello_process, {"greet": handler}, {"name": "World"})

    # Unpacking into a one-item list also checks there's exactly one item.
    [ctx] = received
    assert ctx.instance_id == instance.id
    assert ctx.task_id == "greet"
    assert ctx.variables == {"name": "World"}


def test_context_variables_are_read_only(hello_process: Process) -> None:
    def handler(ctx: ServiceTaskContext) -> None:
        ctx.variables["name"] = "changed"  # type: ignore[index]

    instance = run(hello_process, {"greet": handler}, {"name": "World"})

    assert instance.status == "failed"
    assert instance.failure is not None
    assert instance.failure.error_type == "TypeError"
    assert instance.variables == {"name": "World"}


# --- Failing ------------------------------------------------------------------


def test_failing_handler_fails_the_instance(chain_process: Process) -> None:
    def second(ctx: ServiceTaskContext) -> None:
        raise ValueError("payment declined")

    instance = run(
        chain_process, {"first": lambda ctx: {"step": "first done"}, "second": second}
    )

    assert instance.status == "failed"
    assert instance.failure is not None
    assert instance.failure.task_id == "second"
    assert instance.failure.error_type == "ValueError"
    assert instance.failure.message == "payment declined"
    assert "ValueError: payment declined" in instance.failure.traceback
    # The token stays at the failed task, and earlier results are kept.
    assert instance.tokens == [Token(node_id="second")]
    assert instance.variables == {"step": "first done"}


def test_tasks_after_a_failure_dont_run(chain_process: Process) -> None:
    calls: list[str] = []

    def first(ctx: ServiceTaskContext) -> None:
        raise ValueError("broken")

    def second(ctx: ServiceTaskContext) -> None:
        calls.append("second")

    run(chain_process, {"first": first, "second": second})

    assert calls == []


def test_handler_must_return_a_dict_or_none(hello_process: Process) -> None:
    # Annotated with Any, so mypy accepts the wrong return type on purpose.
    def handler(ctx: ServiceTaskContext) -> Any:
        return ["not", "a", "dict"]

    instance = run(hello_process, {"greet": handler})

    assert instance.status == "failed"
    assert instance.failure is not None
    assert instance.failure.error_type == "TypeError"
    assert instance.failure.message == (
        "The handler returned list, but it must return a dict or None"
    )


def test_keyboard_interrupt_is_not_caught(hello_process: Process) -> None:
    def handler(ctx: ServiceTaskContext) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run(hello_process, {"greet": handler})


def test_missing_handler_raises_before_anything_runs(chain_process: Process) -> None:
    calls: list[str] = []

    with pytest.raises(HandlerNotFoundError) as exc_info:
        run(chain_process, {"first": lambda ctx: calls.append("first")})

    assert exc_info.value.task_id == "second"
    assert calls == []


# --- Instances ----------------------------------------------------------------


def test_every_instance_gets_its_own_id(hello_process: Process) -> None:
    first = run(hello_process, {"greet": greet}, {"name": "World"})
    second = run(hello_process, {"greet": greet}, {"name": "World"})

    assert first.id != second.id
