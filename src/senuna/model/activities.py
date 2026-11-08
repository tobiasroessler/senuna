"""Activities of the BPMN 2.0 metamodel."""

from dataclasses import dataclass

from senuna.model.base import FlowNode


@dataclass(frozen=True, kw_only=True)
class Activity(FlowNode):
    """Base class for work done in a process."""


@dataclass(frozen=True, kw_only=True)
class Task(Activity):
    """An activity that isn't broken down into smaller steps."""


@dataclass(frozen=True, kw_only=True)
class ServiceTask(Task):
    """A task done by software.

    In senuna, a Python handler does the work. It's linked to the task by the
    task id.
    """
