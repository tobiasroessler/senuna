"""Exceptions raised by senuna.

All of them derive from SenunaError, so one ``except SenunaError`` catches
everything senuna raises.

A service task handler that fails during a run is not reported with an
exception: the process instance gets the status ``failed`` instead.

Exceptions with extra attributes pass only those attributes to
``Exception.__init__`` and build their message in ``__str__``. That way they
survive pickling (e.g. when they're passed between processes).
"""

from collections.abc import Sequence


class SenunaError(Exception):
    """Base class for all senuna exceptions."""


class BpmnParseError(SenunaError):
    """The BPMN file can't be read.

    For example: invalid XML, a missing required attribute, or a BPMN element
    senuna doesn't support yet.
    """


class ProcessValidationError(SenunaError):
    """The process breaks one or more of the rules senuna checks when loading it.

    For example: no start event, or a node with two outgoing sequence flows.
    ``problems`` lists every broken rule, so they can all be fixed at once.
    """

    # Sequence[str]: accepts a list or a tuple of strings. It's stored as a
    # tuple so it can't be changed afterwards.
    def __init__(self, process_id: str, problems: Sequence[str]) -> None:
        super().__init__(process_id, tuple(problems))
        self.process_id = process_id
        self.problems = tuple(problems)

    # __str__ decides what str(error) returns, which is also what a traceback
    # shows after the exception's name.
    def __str__(self) -> str:
        lines = "\n".join(f"- {problem}" for problem in self.problems)
        return f"Process '{self.process_id}' is invalid:\n{lines}"


class HandlerNotFoundError(SenunaError):
    """No handler is registered for a service task."""

    def __init__(self, task_id: str) -> None:
        super().__init__(task_id)
        self.task_id = task_id

    def __str__(self) -> str:
        return f"No handler registered for service task '{self.task_id}'"
