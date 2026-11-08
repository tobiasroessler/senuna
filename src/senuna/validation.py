"""Checks whether a process follows the rules of senuna v0.1.

v0.1 only runs linear processes: one start event, then service tasks, then
an end event, each node connected to the next by exactly one sequence flow.

``validate()`` collects every broken rule and raises one
``ProcessValidationError`` that lists them all.
"""

from collections import Counter
from collections.abc import Iterable, Iterator

from senuna.exceptions import ProcessValidationError
from senuna.model import (
    BaseElement,
    EndEvent,
    FlowElement,
    Process,
    SequenceFlow,
    ServiceTask,
    StartEvent,
)

# type[FlowElement]: the class itself (e.g. ServiceTask), not an instance of it.
# isinstance() accepts a tuple of classes and checks against all of them.
SUPPORTED_ELEMENTS: tuple[type[FlowElement], ...] = (
    StartEvent,
    ServiceTask,
    EndEvent,
    SequenceFlow,
)


def validate(process: Process) -> None:
    """Raise ``ProcessValidationError`` if the process breaks any v0.1 rule."""
    # Each _check_ function is a generator: it yields one message per broken
    # rule, or none. "*" inside the list unpacks everything a generator
    # yields, so problems becomes one flat list with all messages, in order.
    problems = [
        *_check_unique_ids(process),
        *_check_supported_elements(process),
        *_check_sequence_flow_ends(process),
        *_check_start_and_end_events(process),
        *_check_sequence_flows_per_node(process),
        *_check_reachability(process),
    ]
    if problems:
        raise ProcessValidationError(process.id, problems)


# Iterator[str]: something you can loop over that gives strings. Functions
# that use "yield" (generators) return one.
def _check_unique_ids(process: Process) -> Iterator[str]:
    # Counter counts how often each id appears, e.g. {"greet": 2, "start": 1}.
    # Its argument is a generator expression: it produces the ids one at a
    # time, without building a list first.
    counts = Counter(element.id for element in process.flow_elements)
    for element_id, count in counts.items():
        if count > 1:
            yield f"Id '{element_id}' is used by {count} elements"


def _check_supported_elements(process: Process) -> Iterator[str]:
    supported = ", ".join(cls.__name__ for cls in SUPPORTED_ELEMENTS)
    for element in process.flow_elements:
        if not isinstance(element, SUPPORTED_ELEMENTS):
            yield f"{_describe(element)} isn't supported yet (supported: {supported})"


def _check_sequence_flow_ends(process: Process) -> Iterator[str]:
    node_ids = {node.id for node in process.flow_nodes}
    for flow in process.sequence_flows:
        if flow.source_ref not in node_ids:
            yield f"{_describe(flow)} starts at unknown flow node '{flow.source_ref}'"
        if flow.target_ref not in node_ids:
            yield f"{_describe(flow)} ends at unknown flow node '{flow.target_ref}'"


def _check_start_and_end_events(process: Process) -> Iterator[str]:
    start_events = process.start_events
    if not start_events:
        yield "The process has no StartEvent"
    elif len(start_events) > 1:
        yield (
            f"The process has {len(start_events)} StartEvents "
            f"({_ids(start_events)}), but exactly one is allowed"
        )

    if not any(isinstance(node, EndEvent) for node in process.flow_nodes):
        yield "The process has no EndEvent"


def _check_sequence_flows_per_node(process: Process) -> Iterator[str]:
    for node in process.flow_nodes:
        incoming = process.incoming(node.id)
        outgoing = process.outgoing(node.id)

        if isinstance(node, StartEvent) and incoming:
            yield (
                f"{_describe(node)} has incoming sequence flows "
                f"({_ids(incoming)}), but a StartEvent can't have any"
            )

        if isinstance(node, EndEvent):
            if outgoing:
                yield (
                    f"{_describe(node)} has outgoing sequence flows "
                    f"({_ids(outgoing)}), but an EndEvent can't have any"
                )
        elif not outgoing:
            yield f"{_describe(node)} has no outgoing sequence flow"
        elif len(outgoing) > 1:
            yield (
                f"{_describe(node)} has {len(outgoing)} outgoing sequence flows "
                f"({_ids(outgoing)}), but only one is allowed"
            )


def _check_reachability(process: Process) -> Iterator[str]:
    # Only meaningful with exactly one start event; other cases are reported
    # by _check_start_and_end_events.
    # No separate cycle check is needed: every node has one outgoing flow, so
    # a cycle always leaves the end event unreachable.
    if len(process.start_events) != 1:
        return  # in a generator, a plain return ends it without yielding

    # Depth-first search: take a node id from the to_visit stack, mark it as
    # reached, and add the targets of its outgoing sequence flows.
    reached: set[str] = set()
    to_visit = [process.start_events[0].id]
    while to_visit:
        node_id = to_visit.pop()
        if node_id not in reached:
            reached.add(node_id)
            to_visit.extend(flow.target_ref for flow in process.outgoing(node_id))

    for node in process.flow_nodes:
        if node.id not in reached:
            yield f"{_describe(node)} can't be reached from the StartEvent"


def _describe(element: BaseElement) -> str:
    """E.g. "ServiceTask 'greet'"."""
    # type(element).__name__ is the name of the element's class as a string.
    return f"{type(element).__name__} '{element.id}'"


def _ids(elements: Iterable[BaseElement]) -> str:
    """E.g. "flow_a, flow_b"."""
    return ", ".join(element.id for element in elements)
