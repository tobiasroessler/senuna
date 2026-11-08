"""Base classes of the BPMN 2.0 metamodel.

Class and attribute names follow the BPMN 2.0 specification, written in
Python style (``sourceRef`` -> ``source_ref``). All model classes are frozen
dataclasses with keyword-only arguments.
"""

from dataclasses import dataclass


# How all model classes are declared:
# - @dataclass writes __init__, __repr__ and __eq__ from the annotated fields
#   (id: str, ...), so they don't have to be written by hand.
# - frozen=True: an instance can't be changed after it's created (assigning a
#   field raises FrozenInstanceError). It also gets a __hash__, so it can be
#   put in a set or used as a dict key.
# - kw_only=True: every argument must be passed by name, e.g.
#   ServiceTask(id="greet", name="Greet"). See SequenceFlow for why this is
#   needed with inheritance.
@dataclass(frozen=True, kw_only=True)
class BaseElement:
    """Root of the BPMN class hierarchy. Every element has an id."""

    id: str


@dataclass(frozen=True, kw_only=True)
class FlowElement(BaseElement):
    """An element inside a process: a flow node or a sequence flow."""

    # str | None: a string, or None when the element has no name (the default).
    name: str | None = None


@dataclass(frozen=True, kw_only=True)
class FlowNode(FlowElement):
    """A flow element that sequence flows connect: an event, activity or gateway.

    Unlike the BPMN metamodel, a flow node doesn't store its incoming and
    outgoing sequence flows. ``Process.incoming()`` and ``Process.outgoing()``
    work them out from the sequence flows, so there's one source of truth.
    """
