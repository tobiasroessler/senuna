"""Sequence flows: the arrows between flow nodes."""

from dataclasses import dataclass

from senuna.model.base import FlowElement


@dataclass(frozen=True, kw_only=True)
class SequenceFlow(FlowElement):
    """Connects two flow nodes and sets the order in which they run.

    ``source_ref`` and ``target_ref`` hold the ids of the two nodes, as in the
    XML, not the node objects.
    """

    # These fields have no default, but the inherited FlowElement.name (which
    # comes before them) has one. Python only allows that because of
    # kw_only=True. Without it: "TypeError: non-default argument 'source_ref'
    # follows default argument".
    source_ref: str
    target_ref: str
