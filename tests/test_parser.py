"""Tests for reading BPMN XML with senuna.parser."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from senuna import BpmnParseError
from senuna.model import EndEvent, Process, SequenceFlow, ServiceTask, StartEvent
from senuna.parser import BPMN_NAMESPACE, parse_file, parse_string

BPMN_DIR = Path(__file__).parent / "bpmn"

SUPPORTED = "bpmn:startEvent, bpmn:serviceTask, bpmn:endEvent, bpmn:sequenceFlow"

# Small helpers that keep the test XML short.


def bpmn(process_body: str, process_attributes: str = 'id="p"') -> str:
    """Wrap BPMN elements in <definitions> and <process>."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="{BPMN_NAMESPACE}" targetNamespace="http://senuna.example">
  <bpmn:process {process_attributes}>
    {process_body}
  </bpmn:process>
</bpmn:definitions>"""


START_TO_END = """
    <bpmn:startEvent id="start" />
    <bpmn:sequenceFlow id="flow1" sourceRef="start" targetRef="end" />
    <bpmn:endEvent id="end" />
"""

START_TO_END_ELEMENTS = (
    StartEvent(id="start"),
    SequenceFlow(id="flow1", source_ref="start", target_ref="end"),
    EndEvent(id="end"),
)


def problems_of(xml: str) -> tuple[str, ...]:
    with pytest.raises(BpmnParseError) as exc_info:
        parse_string(xml)
    return exc_info.value.problems


# --- Valid BPMN ---------------------------------------------------------------


def test_parse_hello_file(hello_process: Process) -> None:
    assert parse_file(BPMN_DIR / "hello.bpmn") == hello_process


def test_parse_file_accepts_a_string_path(hello_process: Process) -> None:
    assert parse_file(str(BPMN_DIR / "hello.bpmn")) == hello_process


def test_parse_file_skips_what_a_modeler_adds() -> None:
    process = parse_file(BPMN_DIR / "hello_modeler.bpmn")

    assert process == Process(
        id="hello",
        name="Hello",
        flow_elements=(
            StartEvent(id="start", name="Start"),
            SequenceFlow(id="flow1", source_ref="start", target_ref="greet"),
            ServiceTask(id="greet", name="Greet"),
            SequenceFlow(id="flow2", source_ref="greet", target_ref="end"),
            EndEvent(id="end", name="End"),
        ),
    )


def test_parse_string_accepts_bytes() -> None:
    process = parse_string(bpmn(START_TO_END).encode())

    assert process.flow_elements == START_TO_END_ELEMENTS


def test_names_are_read() -> None:
    process = parse_string(
        bpmn(
            """
            <bpmn:startEvent id="start" name="Order received" />
            <bpmn:sequenceFlow id="flow1" name="always"
                               sourceRef="start" targetRef="end" />
            <bpmn:endEvent id="end" />
            """,
            process_attributes='id="order" name="Order"',
        )
    )

    assert process.id == "order"
    assert process.name == "Order"
    assert process.flow_elements == (
        StartEvent(id="start", name="Order received"),
        SequenceFlow(id="flow1", name="always", source_ref="start", target_ref="end"),
        EndEvent(id="end"),
    )


def test_the_namespace_prefix_does_not_matter() -> None:
    # The BPMN namespace as the default namespace: no prefix at all.
    xml = f"""
    <definitions xmlns="{BPMN_NAMESPACE}">
      <process id="p">
        <startEvent id="start" />
        <sequenceFlow id="flow1" sourceRef="start" targetRef="end" />
        <endEvent id="end" />
      </process>
    </definitions>
    """

    assert parse_string(xml).flow_elements == START_TO_END_ELEMENTS


def test_incoming_and_outgoing_are_ignored() -> None:
    # Process works out the connections from the sequence flows alone, so
    # even wrong incoming/outgoing entries don't matter.
    process = parse_string(
        bpmn(
            """
            <bpmn:startEvent id="start">
              <bpmn:outgoing>somewhere_else</bpmn:outgoing>
            </bpmn:startEvent>
            <bpmn:sequenceFlow id="flow1" sourceRef="start" targetRef="end" />
            <bpmn:endEvent id="end">
              <bpmn:incoming>flow1</bpmn:incoming>
            </bpmn:endEvent>
            """
        )
    )

    assert process.flow_elements == START_TO_END_ELEMENTS


def test_elements_that_dont_change_the_run_are_skipped() -> None:
    process = parse_string(
        bpmn(
            START_TO_END
            + """
            <bpmn:documentation>About this process</bpmn:documentation>
            <bpmn:extensionElements>
              <other:x xmlns:other="urn:other" />
            </bpmn:extensionElements>
            <bpmn:laneSet id="lanes">
              <bpmn:lane id="lane1">
                <bpmn:flowNodeRef>start</bpmn:flowNodeRef>
              </bpmn:lane>
            </bpmn:laneSet>
            <bpmn:textAnnotation id="note">
              <bpmn:text>A comment</bpmn:text>
            </bpmn:textAnnotation>
            <bpmn:association id="note_link" sourceRef="start" targetRef="note" />
            <bpmn:group id="group1" />
            """
        )
    )

    assert process.flow_elements == START_TO_END_ELEMENTS


def test_other_children_of_definitions_are_skipped() -> None:
    xml = f"""
    <bpmn:definitions xmlns:bpmn="{BPMN_NAMESPACE}">
      <bpmn:message id="message1" name="Order received" />
      <bpmn:collaboration id="collaboration1">
        <bpmn:participant id="pool1" processRef="p" />
      </bpmn:collaboration>
      <bpmn:process id="p">{START_TO_END}</bpmn:process>
    </bpmn:definitions>
    """

    assert parse_string(xml).flow_elements == START_TO_END_ELEMENTS


# --- XML and file structure ---------------------------------------------------


def test_invalid_xml() -> None:
    with pytest.raises(BpmnParseError) as exc_info:
        parse_string("<definitions><process></definitions>")

    [problem] = exc_info.value.problems
    assert problem.startswith("Invalid XML: mismatched tag: line 1")
    assert exc_info.value.path is None
    # The original error from ElementTree is attached ("raise ... from").
    assert isinstance(exc_info.value.__cause__, ET.ParseError)


# tmp_path is a built-in pytest fixture: a new, empty folder for each test.
def test_invalid_xml_file_names_the_file(tmp_path: Path) -> None:
    file = tmp_path / "broken.bpmn"
    file.write_text("<definitions>")

    with pytest.raises(BpmnParseError) as exc_info:
        parse_file(file)

    assert exc_info.value.path == str(file)
    assert str(exc_info.value).startswith(
        f"BPMN file '{file}' can't be read:\n- Invalid XML: "
    )


def test_a_missing_file_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_file(tmp_path / "missing.bpmn")


@pytest.mark.parametrize(
    ("xml", "root"),
    [
        ("<definitions />", "definitions"),  # no namespace
        (f'<bpmn:process xmlns:bpmn="{BPMN_NAMESPACE}" />', "bpmn:process"),
        ('<x:definitions xmlns:x="urn:other" />', "{urn:other}definitions"),
    ],
)
def test_the_root_must_be_bpmn_definitions(xml: str, root: str) -> None:
    assert problems_of(xml) == (
        f"The root element is {root}, but it must be bpmn:definitions "
        f"(namespace {BPMN_NAMESPACE})",
    )


def test_a_file_without_process() -> None:
    xml = f'<bpmn:definitions xmlns:bpmn="{BPMN_NAMESPACE}" />'

    assert problems_of(xml) == ("The file has no bpmn:process",)


def test_a_file_with_two_processes() -> None:
    xml = f"""
    <bpmn:definitions xmlns:bpmn="{BPMN_NAMESPACE}">
      <bpmn:process id="a">{START_TO_END}</bpmn:process>
      <bpmn:process id="b">{START_TO_END}</bpmn:process>
    </bpmn:definitions>
    """

    assert problems_of(xml) == (
        "The file has 2 bpmn:process elements (a, b), but only one is supported",
    )


# --- Elements and attributes --------------------------------------------------


@pytest.mark.parametrize(
    "tag",
    [
        "task",
        "userTask",
        "exclusiveGateway",
        "parallelGateway",
        "subProcess",
        "intermediateCatchEvent",
    ],
)
def test_unsupported_elements_are_rejected(tag: str) -> None:
    xml = bpmn(START_TO_END + f'<bpmn:{tag} id="x" />')

    assert problems_of(xml) == (
        f"bpmn:{tag} 'x' isn't supported yet (supported: {SUPPORTED})",
    )


# pytest.param(..., id="...") gives a parameter set a readable name in the
# test report, e.g. test_unsupported_children_are_rejected[timer start event].
@pytest.mark.parametrize(
    ("element", "problem"),
    [
        pytest.param(
            '<bpmn:startEvent id="start">'
            "<bpmn:timerEventDefinition />"
            "</bpmn:startEvent>",
            "bpmn:startEvent 'start' contains bpmn:timerEventDefinition, "
            "which isn't supported yet",
            id="timer start event",
        ),
        pytest.param(
            '<bpmn:endEvent id="end"><bpmn:errorEventDefinition /></bpmn:endEvent>',
            "bpmn:endEvent 'end' contains bpmn:errorEventDefinition, "
            "which isn't supported yet",
            id="error end event",
        ),
        pytest.param(
            '<bpmn:serviceTask id="task">'
            "<bpmn:multiInstanceLoopCharacteristics />"
            "</bpmn:serviceTask>",
            "bpmn:serviceTask 'task' contains "
            "bpmn:multiInstanceLoopCharacteristics, which isn't supported yet",
            id="multi-instance service task",
        ),
        pytest.param(
            '<bpmn:sequenceFlow id="flow" sourceRef="a" targetRef="b">'
            "<bpmn:conditionExpression>${ok}</bpmn:conditionExpression>"
            "</bpmn:sequenceFlow>",
            "bpmn:sequenceFlow 'flow' contains bpmn:conditionExpression, "
            "which isn't supported yet",
            id="conditional sequence flow",
        ),
    ],
)
def test_unsupported_children_are_rejected(element: str, problem: str) -> None:
    assert problems_of(bpmn(element)) == (problem,)


@pytest.mark.parametrize(
    ("element", "problem"),
    [
        pytest.param(
            '<bpmn:serviceTask name="Greet" />',
            "bpmn:serviceTask has no id",
            id="flow node id",
        ),
        pytest.param(
            '<bpmn:endEvent id="" />',
            "bpmn:endEvent has no id",
            id="empty id",
        ),
        pytest.param(
            '<bpmn:sequenceFlow sourceRef="a" targetRef="b" />',
            "bpmn:sequenceFlow has no id",
            id="sequence flow id",
        ),
        pytest.param(
            '<bpmn:sequenceFlow id="flow" targetRef="b" />',
            "bpmn:sequenceFlow 'flow' has no sourceRef",
            id="sourceRef",
        ),
        pytest.param(
            '<bpmn:sequenceFlow id="flow" sourceRef="a" />',
            "bpmn:sequenceFlow 'flow' has no targetRef",
            id="targetRef",
        ),
    ],
)
def test_missing_attributes_are_rejected(element: str, problem: str) -> None:
    assert problems_of(bpmn(element)) == (problem,)


def test_a_process_without_id_is_rejected() -> None:
    xml = bpmn(START_TO_END, process_attributes='name="No id"')

    assert problems_of(xml) == ("bpmn:process has no id",)


def test_all_problems_are_reported_together() -> None:
    xml = bpmn(
        """
        <bpmn:startEvent id="start"><bpmn:timerEventDefinition /></bpmn:startEvent>
        <bpmn:sequenceFlow id="flow1" sourceRef="start" />
        <bpmn:exclusiveGateway id="check" />
        <bpmn:endEvent />
        """
    )

    # In the order they appear in the file.
    assert problems_of(xml) == (
        "bpmn:startEvent 'start' contains bpmn:timerEventDefinition, "
        "which isn't supported yet",
        "bpmn:sequenceFlow 'flow1' has no targetRef",
        f"bpmn:exclusiveGateway 'check' isn't supported yet (supported: {SUPPORTED})",
        "bpmn:endEvent has no id",
    )
