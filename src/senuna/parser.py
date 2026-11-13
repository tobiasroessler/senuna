"""Reads BPMN 2.0 XML and turns it into a ``Process``.

v0.1 reads one ``<process>`` per file with start events, service tasks, end
events and sequence flows. Everything else that could change how the process
runs is rejected with a ``BpmnParseError``, so nothing is silently ignored.
Elements that don't change how it runs (the diagram, documentation, text
annotations, ...) are skipped.

The parser only builds the model. Whether the process makes sense (one start
event, everything connected, ...) is checked by ``senuna.validation``.
"""

import os
import xml.etree.ElementTree as ET

from senuna.exceptions import BpmnParseError
from senuna.model import (
    EndEvent,
    FlowElement,
    FlowNode,
    Process,
    SequenceFlow,
    ServiceTask,
    StartEvent,
)

BPMN_NAMESPACE = "http://www.omg.org/spec/BPMN/20100524/MODEL"


# ElementTree writes a tag with a namespace as "{namespace}localName" (Clark
# notation), whatever prefix the file uses: <bpmn:startEvent>, <semantic:startEvent>
# and <startEvent xmlns="..."> all become "{http://www.omg.org/...}startEvent".
def _bpmn(local_name: str) -> str:
    return f"{{{BPMN_NAMESPACE}}}{local_name}"  # {{ and }} are literal braces


# The tags the parser turns into model classes.
_FLOW_NODE_CLASSES: dict[str, type[FlowNode]] = {
    _bpmn("startEvent"): StartEvent,
    _bpmn("serviceTask"): ServiceTask,
    _bpmn("endEvent"): EndEvent,
}
_SEQUENCE_FLOW = _bpmn("sequenceFlow")

# Children that don't change how the process runs, so they're skipped.
# frozenset: a set that can't be changed; "|" combines two sets.
_METADATA = frozenset({_bpmn("documentation"), _bpmn("extensionElements")})
_SKIPPED_IN_PROCESS = _METADATA | {
    _bpmn("laneSet"),  # lanes: who does what, for people reading the diagram
    _bpmn("textAnnotation"),  # comments in the diagram
    _bpmn("association"),  # the dotted line from a comment to an element
    _bpmn("group"),  # a dashed box around elements
}
# incoming/outgoing repeat what the sequence flows already say, and Process
# works them out from the sequence flows, so they're skipped too.
_SKIPPED_IN_FLOW_NODE = _METADATA | {_bpmn("incoming"), _bpmn("outgoing")}
_SKIPPED_IN_SEQUENCE_FLOW = _METADATA

_SUPPORTED = "bpmn:startEvent, bpmn:serviceTask, bpmn:endEvent, bpmn:sequenceFlow"


# os.PathLike[str]: a path object like pathlib.Path. Together with str, the
# function accepts both "hello.bpmn" and Path("hello.bpmn").
def parse_file(path: str | os.PathLike[str]) -> Process:
    """Read a BPMN 2.0 file and return its process.

    Raises ``BpmnParseError`` if the file isn't valid XML or isn't a BPMN
    file senuna can run. If the file can't be opened, the ``OSError`` (e.g.
    ``FileNotFoundError``) isn't caught.
    """
    path = os.fspath(path)  # Path("hello.bpmn") -> "hello.bpmn"
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise BpmnParseError([f"Invalid XML: {error}"], path) from error
    return _parse_definitions(root, path)


def parse_string(xml: str | bytes) -> Process:
    """Read BPMN 2.0 XML from a string and return its process.

    Raises ``BpmnParseError`` like ``parse_file()``.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise BpmnParseError([f"Invalid XML: {error}"]) from error
    return _parse_definitions(root, path=None)


def _parse_definitions(root: ET.Element, path: str | None) -> Process:
    """Find the one process in <definitions> and parse it.

    Other children of <definitions> (the diagram, pools, message
    definitions, ...) are skipped.
    """
    if root.tag != _bpmn("definitions"):
        raise BpmnParseError(
            [
                f"The root element is {_tag_name(root.tag)}, but it must be "
                f"bpmn:definitions (namespace {BPMN_NAMESPACE})"
            ],
            path,
        )

    processes = root.findall(_bpmn("process"))  # direct children only
    if not processes:
        raise BpmnParseError(["The file has no bpmn:process"], path)
    if len(processes) > 1:
        ids = ", ".join(process.get("id", "?") for process in processes)
        raise BpmnParseError(
            [
                f"The file has {len(processes)} bpmn:process elements ({ids}), "
                "but only one is supported"
            ],
            path,
        )

    # Every function below adds what it finds to this list instead of raising,
    # so one BpmnParseError reports all problems in the file.
    problems: list[str] = []
    process = _parse_process(processes[0], problems)
    if problems:
        raise BpmnParseError(problems, path)
    return process


def _parse_process(element: ET.Element, problems: list[str]) -> Process:
    process_id = _required(element, "id", problems)
    flow_elements: list[FlowElement] = []

    # Looping over an element gives its child elements, in file order.
    for child in element:
        if child.tag in _FLOW_NODE_CLASSES:
            flow_elements.append(_parse_flow_node(child, problems))
        elif child.tag == _SEQUENCE_FLOW:
            flow_elements.append(_parse_sequence_flow(child, problems))
        elif child.tag not in _SKIPPED_IN_PROCESS:
            problems.append(
                f"{_describe(child)} isn't supported yet (supported: {_SUPPORTED})"
            )

    return Process(
        id=process_id,
        name=element.get("name"),
        flow_elements=tuple(flow_elements),
    )


def _parse_flow_node(element: ET.Element, problems: list[str]) -> FlowNode:
    node_class = _FLOW_NODE_CLASSES[element.tag]
    node = node_class(id=_required(element, "id", problems), name=element.get("name"))
    # E.g. a timer definition turns a start event into a timer start event,
    # which v0.1 can't run.
    _check_children(element, _SKIPPED_IN_FLOW_NODE, problems)
    return node


def _parse_sequence_flow(element: ET.Element, problems: list[str]) -> SequenceFlow:
    flow = SequenceFlow(
        id=_required(element, "id", problems),
        name=element.get("name"),
        source_ref=_required(element, "sourceRef", problems),
        target_ref=_required(element, "targetRef", problems),
    )
    # E.g. a condition, which comes with gateways.
    _check_children(element, _SKIPPED_IN_SEQUENCE_FLOW, problems)
    return flow


def _required(element: ET.Element, attribute: str, problems: list[str]) -> str:
    """Return the attribute's value; a missing or empty one is a problem.

    The empty string returned then never reaches the model, because the
    parser raises before returning the process.
    """
    value = element.get(attribute, "")
    if not value:
        problems.append(f"{_describe(element)} has no {attribute}")
    return value


def _check_children(
    element: ET.Element, skipped: frozenset[str], problems: list[str]
) -> None:
    for child in element:
        if child.tag not in skipped:
            problems.append(
                f"{_describe(element)} contains {_tag_name(child.tag)}, "
                "which isn't supported yet"
            )


def _describe(element: ET.Element) -> str:
    """E.g. "bpmn:serviceTask 'greet'", or "bpmn:serviceTask" without an id."""
    element_id = element.get("id")
    name = _tag_name(element.tag)
    return f"{name} '{element_id}'" if element_id else name


def _tag_name(tag: str) -> str:
    """Write BPMN tags with the usual "bpmn:" prefix, other tags unchanged."""
    # removeprefix() returns the string unchanged if it doesn't start with it.
    local_name = tag.removeprefix(f"{{{BPMN_NAMESPACE}}}")
    return f"bpmn:{local_name}" if local_name != tag else tag
