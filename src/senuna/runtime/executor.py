"""Runs a process: moves tokens through it and calls service task handlers.

``run()`` expects a validated process (see ``senuna.validation``). The engine
validates every process when it's loaded.
"""

import traceback
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from senuna.exceptions import HandlerNotFoundError
from senuna.model import EndEvent, FlowNode, Process, ServiceTask, StartEvent
from senuna.runtime.context import ServiceTaskContext, ServiceTaskHandler
from senuna.runtime.instance import Failure, InstanceStatus, ProcessInstance, Token


def run(
    process: Process,
    handlers: Mapping[str, ServiceTaskHandler],
    variables: Mapping[str, Any] | None = None,
) -> ProcessInstance:
    """Run a process from its start event until it completes or fails.

    ``handlers`` maps service task ids to their handlers. If a service task
    has none, ``HandlerNotFoundError`` is raised before anything runs.

    A handler that fails doesn't raise: the instance is returned with the
    status ``failed`` and a ``failure`` that says what went wrong.
    """
    _check_handlers(process, handlers)

    instance = ProcessInstance(
        process_id=process.id,
        variables=dict(variables or {}),  # a copy, so the caller's dict isn't changed
        # The run starts with one new token at the start event. [0] is safe:
        # a validated process has exactly one start event.
        tokens=[Token(node_id=process.start_events[0].id)],
    )

    while instance.tokens:
        token = instance.tokens[0]
        node = process.get_flow_node(token.node_id)
        try:
            next_node_ids = _run_node(node, process, instance, handlers)
        except _ServiceTaskFailed as failed:
            # The token stays at the failed task, so the instance shows where
            # it stopped.
            instance.status = InstanceStatus.FAILED
            instance.failure = failed.failure
            return instance

        # The token has passed the node: replace it with one per next node.
        instance.tokens.pop(0)
        instance.tokens.extend(Token(node_id=node_id) for node_id in next_node_ids)

    instance.status = InstanceStatus.COMPLETED
    return instance


def _check_handlers(
    process: Process, handlers: Mapping[str, ServiceTaskHandler]
) -> None:
    for node in process.flow_nodes:
        if isinstance(node, ServiceTask) and node.id not in handlers:
            raise HandlerNotFoundError(node.id)


def _run_node(
    node: FlowNode,
    process: Process,
    instance: ProcessInstance,
    handlers: Mapping[str, ServiceTaskHandler],
) -> list[str]:
    """Run one flow node. Return the ids of the nodes the process goes on to."""
    # match/case (structural pattern matching): "case ServiceTask():" matches
    # when node is a ServiceTask, like isinstance(node, ServiceTask).
    # "case _:" matches anything else.
    match node:
        case StartEvent():
            return _next_node_ids(process, node)
        case ServiceTask():
            _run_service_task(node, instance, handlers[node.id])
            return _next_node_ids(process, node)
        case EndEvent():
            return []  # the token is used up
        case _:
            raise TypeError(f"Can't run {type(node).__name__} '{node.id}'")


def _next_node_ids(process: Process, node: FlowNode) -> list[str]:
    """Return the targets of the node's outgoing sequence flows.

    In v0.1 there's exactly one. With several, each target gets its own
    token, which is how BPMN runs unconditional sequence flows in parallel.
    """
    return [flow.target_ref for flow in process.outgoing(node.id)]


def _run_service_task(
    task: ServiceTask, instance: ProcessInstance, handler: ServiceTaskHandler
) -> None:
    context = ServiceTaskContext(
        instance_id=instance.id,
        task_id=task.id,
        # MappingProxyType: a read-only view of a dict. It's a view of a copy,
        # so it doesn't change while the handler runs.
        variables=MappingProxyType(dict(instance.variables)),
    )

    # Every Exception from the handler fails the instance. BaseExceptions like
    # KeyboardInterrupt aren't caught, so Ctrl+C still stops the program.
    try:
        result = handler(context)
        # Handlers aren't type-checked when they run, so check the result.
        if result is not None and not isinstance(result, Mapping):
            raise TypeError(
                f"The handler returned {type(result).__name__}, "
                "but it must return a dict or None"
            )
        if result is not None:
            instance.variables.update(result)
    except Exception as error:
        # "from error" keeps the original exception attached as __cause__.
        raise _ServiceTaskFailed(_failure(task.id, error)) from error


def _failure(task_id: str, error: Exception) -> Failure:
    return Failure(
        task_id=task_id,
        error_type=type(error).__name__,
        message=str(error),
        # format_exception() returns the traceback as a list of text lines.
        traceback="".join(traceback.format_exception(error)),
    )


class _ServiceTaskFailed(Exception):
    """Carries a Failure from _run_service_task() up to run().

    Internal: it never leaves this module.
    """

    def __init__(self, failure: Failure) -> None:
        super().__init__(failure.message)
        self.failure = failure
