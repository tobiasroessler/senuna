"""The process: flow nodes connected by sequence flows."""

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cached_property

from senuna.model.base import BaseElement, FlowElement, FlowNode
from senuna.model.events import StartEvent
from senuna.model.sequence_flow import SequenceFlow


@dataclass(frozen=True, kw_only=True)
class Process(BaseElement):
    """A BPMN process: flow nodes connected by sequence flows.

    A process only stores its elements and looks them up. It doesn't check
    senuna's rules (exactly one start event, unique ids, ...); that's done in
    ``senuna.validation``. Until then, lookups by id may be wrong, for example
    when two nodes share an id.
    """

    name: str | None = None

    # tuple[FlowElement, ...]: a tuple of any length ("...") whose items are
    # all FlowElements. A tuple and not a list, because:
    # - frozen=True only stops the field from being replaced. A list could
    #   still be changed in place (append); a tuple can't.
    # - The generated __hash__ needs every field to be hashable; a list isn't.
    # - A default of () is safe. A list default ([]) would be shared by all
    #   instances, so dataclasses rejects it.
    flow_elements: tuple[FlowElement, ...] = ()

    # @cached_property: computed on first access, then stored on the instance.
    # Later accesses return the stored value. It's used without parentheses:
    # process.flow_nodes. Safe here because a frozen process can't change, so
    # the stored value never becomes outdated. (It writes straight into the
    # instance's __dict__, which bypasses the frozen check.)
    @cached_property
    def flow_nodes(self) -> tuple[FlowNode, ...]:
        """All flow nodes, in the order of ``flow_elements``."""
        # A generator expression: it produces the matching elements one at a
        # time, and tuple() collects them.
        return tuple(e for e in self.flow_elements if isinstance(e, FlowNode))

    @cached_property
    def sequence_flows(self) -> tuple[SequenceFlow, ...]:
        """All sequence flows, in the order of ``flow_elements``."""
        return tuple(e for e in self.flow_elements if isinstance(e, SequenceFlow))

    @cached_property
    def start_events(self) -> tuple[StartEvent, ...]:
        """All start events, in the order of ``flow_elements``."""
        return tuple(n for n in self.flow_nodes if isinstance(n, StartEvent))

    def get_flow_node(self, node_id: str) -> FlowNode:
        """Return the flow node with this id. Raises ``KeyError`` if there's none."""
        return self._flow_nodes_by_id[node_id]

    def outgoing(self, node_id: str) -> tuple[SequenceFlow, ...]:
        """Return the sequence flows that leave this node."""
        return self._outgoing_by_node_id.get(node_id, ())

    def incoming(self, node_id: str) -> tuple[SequenceFlow, ...]:
        """Return the sequence flows that arrive at this node."""
        return self._incoming_by_node_id.get(node_id, ())

    # The lookup tables are cached on first use. cached_property isn't a
    # dataclass field, so the tables don't affect equality, hashing or repr.

    @cached_property
    def _flow_nodes_by_id(self) -> dict[str, FlowNode]:
        return {node.id: node for node in self.flow_nodes}

    @cached_property
    def _outgoing_by_node_id(self) -> dict[str, tuple[SequenceFlow, ...]]:
        # lambda: a small function without a name. Here it tells _group which
        # node id to group each sequence flow by.
        return _group(self.sequence_flows, by=lambda flow: flow.source_ref)

    @cached_property
    def _incoming_by_node_id(self) -> dict[str, tuple[SequenceFlow, ...]]:
        return _group(self.sequence_flows, by=lambda flow: flow.target_ref)


def _group(
    flows: Iterable[SequenceFlow], by: Callable[[SequenceFlow], str]
) -> dict[str, tuple[SequenceFlow, ...]]:
    """Group sequence flows by a node id, keeping their order."""
    # defaultdict(list): a dict that creates an empty list for a missing key,
    # so groups[...].append() works without checking whether the key exists.
    groups: defaultdict[str, list[SequenceFlow]] = defaultdict(list)
    for flow in flows:
        groups[by(flow)].append(flow)
    return {node_id: tuple(group) for node_id, group in groups.items()}
