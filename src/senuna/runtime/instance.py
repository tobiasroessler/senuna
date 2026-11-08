"""The state of a running process: the process instance and its tokens."""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class InstanceStatus(StrEnum):
    """Where a process instance stands."""

    # StrEnum: each member is also a str, so it compares equal to its value:
    # InstanceStatus.COMPLETED == "completed" is True.
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, kw_only=True)
class Token:
    """Marks the flow node a process instance is at (BPMN execution semantics).

    A token never changes: when the process goes on, it's replaced by a new
    token at the next node. v0.1 processes only ever have one token.
    """

    node_id: str


@dataclass(frozen=True, kw_only=True)
class Failure:
    """Why a process instance failed: which service task, and what went wrong.

    Only strings, so it can be stored as JSON later.
    """

    task_id: str
    error_type: str  # the exception's class name, e.g. "ValueError"
    message: str
    traceback: str  # the full traceback as text, as Python would print it


# Not frozen: status, variables and tokens change while the instance runs.
@dataclass(kw_only=True)
class ProcessInstance:
    """One run of a process."""

    # field(default_factory=...) calls the function for every new instance,
    # so each one gets its own id, dict and list. A plain default like {}
    # would be shared by all instances.
    # uuid4(): a random id that's practically unique, e.g.
    # "1b4e28ba-2fa1-41d2-883f-0016d3cca427".
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    process_id: str
    status: InstanceStatus = InstanceStatus.RUNNING
    variables: dict[str, Any] = field(default_factory=dict)
    tokens: list[Token] = field(default_factory=list)
    failure: Failure | None = None
