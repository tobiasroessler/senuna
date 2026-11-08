"""What a service task handler receives, and what it may return."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True)
class ServiceTaskContext:
    """Passed to a service task handler as its only argument (``ctx``).

    ``variables`` is a read-only snapshot of the instance variables when the
    handler starts. A handler doesn't change it; it returns a dict with the
    variables to add or update instead.
    """

    instance_id: str
    task_id: str
    # Mapping: a read-only dict type. It has no methods to change the content.
    variables: Mapping[str, Any]


# A type alias: a name for a longer type. Callable[[A], R] is a function that
# takes one A and returns an R. A handler returns the variables to merge into
# the instance, or None.
ServiceTaskHandler = Callable[[ServiceTaskContext], Mapping[str, Any] | None]
