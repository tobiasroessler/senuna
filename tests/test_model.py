"""Tests for the BPMN model classes."""

import dataclasses

import pytest

from senuna.model import (
    Activity,
    BaseElement,
    EndEvent,
    Event,
    FlowElement,
    FlowNode,
    Process,
    SequenceFlow,
    ServiceTask,
    StartEvent,
    Task,
)

# --- Elements ---------------------------------------------------------------


# parametrize runs the test once per tuple in the list, passing its values
# as the arguments named in the first string.
@pytest.mark.parametrize(
    ("element_class", "base_classes"),
    [
        (StartEvent, (Event, FlowNode, FlowElement, BaseElement)),
        (EndEvent, (Event, FlowNode, FlowElement, BaseElement)),
        (ServiceTask, (Task, Activity, FlowNode, FlowElement, BaseElement)),
        (SequenceFlow, (FlowElement, BaseElement)),
        (Process, (BaseElement,)),
    ],
)
def test_class_hierarchy_follows_the_bpmn_spec(
    element_class: type, base_classes: tuple[type, ...]
) -> None:
    for base_class in base_classes:
        assert issubclass(element_class, base_class)


def test_sequence_flow_is_not_a_flow_node() -> None:
    assert not issubclass(SequenceFlow, FlowNode)


def test_name_is_optional() -> None:
    assert StartEvent(id="start").name is None
    assert ServiceTask(id="greet", name="Greet").name == "Greet"


def test_elements_are_immutable() -> None:
    task = ServiceTask(id="greet")

    # pytest.raises: the test passes only if the block raises this exception.
    # The type: ignore comment stops mypy from flagging the assignment, which
    # is exactly what's being tested.
    with pytest.raises(dataclasses.FrozenInstanceError):
        task.id = "other"  # type: ignore[misc]


def test_elements_with_the_same_values_are_equal() -> None:
    assert ServiceTask(id="greet") == ServiceTask(id="greet")
    assert ServiceTask(id="greet") != ServiceTask(id="other")


def test_elements_of_different_types_are_not_equal() -> None:
    start: FlowNode = StartEvent(id="node")
    end: FlowNode = EndEvent(id="node")

    assert start != end


# --- Process ------------------------------------------------------------------


def test_process_separates_flow_nodes_and_sequence_flows(
    hello_process: Process,
) -> None:
    assert [node.id for node in hello_process.flow_nodes] == ["start", "greet", "end"]
    assert [flow.id for flow in hello_process.sequence_flows] == ["flow1", "flow2"]


def test_process_finds_its_start_events(hello_process: Process) -> None:
    assert hello_process.start_events == (StartEvent(id="start"),)


def test_get_flow_node_returns_the_node(hello_process: Process) -> None:
    assert hello_process.get_flow_node("greet") == ServiceTask(id="greet", name="Greet")


@pytest.mark.parametrize("element_id", ["unknown", "flow1"])
def test_get_flow_node_raises_key_error_for_other_ids(
    hello_process: Process, element_id: str
) -> None:
    # "flow1" exists, but it's a sequence flow, not a flow node.
    with pytest.raises(KeyError):
        hello_process.get_flow_node(element_id)


def test_outgoing_and_incoming_sequence_flows(hello_process: Process) -> None:
    assert [flow.id for flow in hello_process.outgoing("greet")] == ["flow2"]
    assert [flow.id for flow in hello_process.incoming("greet")] == ["flow1"]


def test_start_event_has_no_incoming_and_end_event_no_outgoing(
    hello_process: Process,
) -> None:
    assert hello_process.incoming("start") == ()
    assert hello_process.outgoing("end") == ()


def test_outgoing_keeps_the_order_of_several_flows() -> None:
    process = Process(
        id="split",
        flow_elements=(
            StartEvent(id="start"),
            SequenceFlow(id="flow_a", source_ref="start", target_ref="end_a"),
            SequenceFlow(id="flow_b", source_ref="start", target_ref="end_b"),
            EndEvent(id="end_a"),
            EndEvent(id="end_b"),
        ),
    )

    assert [flow.id for flow in process.outgoing("start")] == ["flow_a", "flow_b"]


def test_empty_process() -> None:
    process = Process(id="empty")

    assert process.flow_nodes == ()
    assert process.sequence_flows == ()
    assert process.start_events == ()


def test_cached_lookups_dont_affect_equality(hello_process: Process) -> None:
    hello_process.outgoing("start")  # fills the lookup cache
    # dataclasses.replace() creates a new instance with the same field values
    # (fields passed as keyword arguments would be changed).
    same_process = dataclasses.replace(hello_process)

    assert hello_process == same_process
    assert hash(hello_process) == hash(same_process)
