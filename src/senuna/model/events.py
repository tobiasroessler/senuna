"""Events of the BPMN 2.0 metamodel."""

from dataclasses import dataclass

from senuna.model.base import FlowNode


@dataclass(frozen=True, kw_only=True)
class Event(FlowNode):
    """Base class for events: something that happens during a process."""


@dataclass(frozen=True, kw_only=True)
class StartEvent(Event):
    """Where a process starts."""


@dataclass(frozen=True, kw_only=True)
class EndEvent(Event):
    """Where a path through the process ends."""
