"""Tests for the v0.1 rules in senuna.validation."""

import pytest

from senuna import ProcessValidationError
from senuna.model import (
    EndEvent,
    FlowElement,
    Process,
    SequenceFlow,
    ServiceTask,
    StartEvent,
    Task,
)
from senuna.validation import validate

# Small helpers that keep the test processes short.


# *elements collects any number of arguments into a tuple, so this is called
# as process(StartEvent(...), flow(...), ...). The other way round,
# process(*hello_process.flow_elements, extra) unpacks a tuple into separate
# arguments.
def process(*elements: FlowElement) -> Process:
    return Process(id="p", flow_elements=elements)


def flow(flow_id: str, source: str, target: str) -> SequenceFlow:
    return SequenceFlow(id=flow_id, source_ref=source, target_ref=target)


def problems_of(invalid_process: Process) -> tuple[str, ...]:
    # pytest.raises fails the test unless the block raises this exception.
    # "as exc_info" keeps it: exc_info.value is the exception itself.
    with pytest.raises(ProcessValidationError) as exc_info:
        validate(invalid_process)
    return exc_info.value.problems


# --- Valid processes ----------------------------------------------------------


def test_hello_process_is_valid(hello_process: Process) -> None:
    validate(hello_process)


def test_chain_of_service_tasks_is_valid() -> None:
    validate(
        process(
            StartEvent(id="start"),
            flow("flow1", "start", "a"),
            ServiceTask(id="a"),
            flow("flow2", "a", "b"),
            ServiceTask(id="b"),
            flow("flow3", "b", "end"),
            EndEvent(id="end"),
        )
    )


# --- Broken rules -------------------------------------------------------------


def test_empty_process() -> None:
    assert problems_of(process()) == (
        "The process has no StartEvent",
        "The process has no EndEvent",
    )


def test_duplicate_ids(hello_process: Process) -> None:
    duplicate = process(*hello_process.flow_elements, ServiceTask(id="greet"))

    assert problems_of(duplicate) == ("Id 'greet' is used by 2 elements",)


def test_unsupported_element() -> None:
    plain_task = process(
        StartEvent(id="start"),
        flow("flow1", "start", "task"),
        Task(id="task"),
        flow("flow2", "task", "end"),
        EndEvent(id="end"),
    )

    assert problems_of(plain_task) == (
        "Task 'task' isn't supported yet "
        "(supported: StartEvent, ServiceTask, EndEvent, SequenceFlow)",
    )


def test_sequence_flow_from_unknown_node(hello_process: Process) -> None:
    from_ghost = process(*hello_process.flow_elements, flow("flow3", "ghost", "end"))

    assert problems_of(from_ghost) == (
        "SequenceFlow 'flow3' starts at unknown flow node 'ghost'",
    )


def test_sequence_flow_to_unknown_node() -> None:
    to_missing = process(
        StartEvent(id="start"),
        flow("flow1", "start", "greet"),
        ServiceTask(id="greet"),
        flow("flow2", "greet", "missing"),
        EndEvent(id="end"),
    )

    assert problems_of(to_missing) == (
        "SequenceFlow 'flow2' ends at unknown flow node 'missing'",
        "EndEvent 'end' can't be reached from the StartEvent",
    )


def test_two_start_events() -> None:
    two_starts = process(
        StartEvent(id="start1"),
        StartEvent(id="start2"),
        flow("flow1", "start1", "greet"),
        flow("flow2", "start2", "greet"),
        ServiceTask(id="greet"),
        flow("flow3", "greet", "end"),
        EndEvent(id="end"),
    )

    # Reachability isn't checked without exactly one start event.
    assert problems_of(two_starts) == (
        "The process has 2 StartEvents (start1, start2), but exactly one is allowed",
    )


def test_no_end_event() -> None:
    no_end = process(
        StartEvent(id="start"),
        flow("flow1", "start", "greet"),
        ServiceTask(id="greet"),
    )

    assert problems_of(no_end) == (
        "The process has no EndEvent",
        "ServiceTask 'greet' has no outgoing sequence flow",
    )


def test_start_event_with_incoming_flow() -> None:
    back_to_start = process(
        StartEvent(id="start"),
        flow("flow1", "start", "greet"),
        ServiceTask(id="greet"),
        flow("flow2", "greet", "start"),
        EndEvent(id="end"),
    )

    assert problems_of(back_to_start) == (
        "StartEvent 'start' has incoming sequence flows (flow2), "
        "but a StartEvent can't have any",
        "EndEvent 'end' can't be reached from the StartEvent",
    )


def test_end_event_with_outgoing_flow(hello_process: Process) -> None:
    from_end = process(*hello_process.flow_elements, flow("flow3", "end", "greet"))

    assert problems_of(from_end) == (
        "EndEvent 'end' has outgoing sequence flows (flow3), "
        "but an EndEvent can't have any",
    )


def test_node_without_outgoing_flow() -> None:
    dead_end = process(
        StartEvent(id="start"),
        flow("flow1", "start", "greet"),
        ServiceTask(id="greet"),
        EndEvent(id="end"),
    )

    assert problems_of(dead_end) == (
        "ServiceTask 'greet' has no outgoing sequence flow",
        "EndEvent 'end' can't be reached from the StartEvent",
    )


def test_node_with_two_outgoing_flows() -> None:
    split = process(
        StartEvent(id="start"),
        flow("flow1", "start", "greet"),
        ServiceTask(id="greet"),
        flow("flow_a", "greet", "end_a"),
        flow("flow_b", "greet", "end_b"),
        EndEvent(id="end_a"),
        EndEvent(id="end_b"),
    )

    assert problems_of(split) == (
        "ServiceTask 'greet' has 2 outgoing sequence flows (flow_a, flow_b), "
        "but only one is allowed",
    )


def test_unreachable_node(hello_process: Process) -> None:
    orphan = process(
        *hello_process.flow_elements,
        ServiceTask(id="orphan"),
        flow("flow3", "orphan", "end"),
    )

    assert problems_of(orphan) == (
        "ServiceTask 'orphan' can't be reached from the StartEvent",
    )


def test_cycle_leaves_the_end_event_unreachable() -> None:
    cycle = process(
        StartEvent(id="start"),
        flow("flow1", "start", "a"),
        ServiceTask(id="a"),
        flow("flow2", "a", "b"),
        ServiceTask(id="b"),
        flow("flow3", "b", "a"),
        EndEvent(id="end"),
    )

    assert problems_of(cycle) == (
        "EndEvent 'end' can't be reached from the StartEvent",
    )


def test_error_names_the_process() -> None:
    with pytest.raises(ProcessValidationError) as exc_info:
        validate(Process(id="order"))

    assert exc_info.value.process_id == "order"
