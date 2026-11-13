"""The Senuna class: the one class most users need.

It connects the other layers: it reads and checks BPMN files (parser,
validation), keeps the service task handlers, and runs processes (runtime).
"""

import os
from collections.abc import Callable, Mapping
from typing import Any

from senuna.exceptions import HandlerAlreadyRegisteredError
from senuna.model import Process
from senuna.parser import parse_file
from senuna.runtime import ProcessInstance, ServiceTaskHandler
from senuna.runtime import run as run_process  # "as": Senuna has its own run()
from senuna.validation import validate


class Senuna:
    """A process engine: register handlers, load processes, run them.

    Usage::

        from senuna import Senuna

        process_engine = Senuna()

        @process_engine.service_task("greet")
        def greet(ctx):
            return {"greeting": f"Hello {ctx.variables['name']}"}

        process = process_engine.load("hello.bpmn")
        instance = process_engine.run(process, variables={"name": "World"})
    """

    def __init__(self) -> None:
        # Service task id -> handler. Every engine has its own handlers.
        self._handlers: dict[str, ServiceTaskHandler] = {}

    # [H: ServiceTaskHandler] declares a type parameter (Python 3.12 syntax).
    # H stands for the type of the decorated function, which must fit
    # ServiceTaskHandler. Callable[[H], H] tells type checkers that the
    # function comes back unchanged, with its exact type.
    def service_task[H: ServiceTaskHandler](self, task_id: str) -> Callable[[H], H]:
        """Register the decorated function as the handler of a service task.

        ``task_id`` is the id of the ``<serviceTask>`` in the BPMN file. The
        function is returned unchanged, so it can still be called directly,
        e.g. in a test. Raises ``HandlerAlreadyRegisteredError`` if the task
        already has a handler.
        """

        # A decorator with an argument: service_task("greet") returns
        # register, and Python then calls register() with the function below
        # the "@" line. So @process_engine.service_task("greet") above
        # "def greet" does the same as
        # greet = process_engine.service_task("greet")(greet).
        # register can use task_id and self after service_task() has returned:
        # an inner function remembers the variables around it (a closure).
        def register(handler: H) -> H:
            if task_id in self._handlers:
                raise HandlerAlreadyRegisteredError(task_id)
            self._handlers[task_id] = handler
            return handler

        return register

    def load(self, path: str | os.PathLike[str]) -> Process:
        """Read a BPMN file and return its process, checked and ready to run.

        Raises ``BpmnParseError`` if the file can't be read, and
        ``ProcessValidationError`` if the process breaks a v0.1 rule.
        Handlers don't have to be registered yet; ``run()`` checks them.
        """
        process = parse_file(path)
        validate(process)
        return process

    def run(
        self, process: Process, variables: Mapping[str, Any] | None = None
    ) -> ProcessInstance:
        """Run a process from start to end and return the instance.

        ``variables`` are the starting variables; the caller's dict isn't
        changed. The instance's status is ``completed``, or ``failed`` if a
        handler raised an exception (see ``instance.failure``).

        Nothing runs, and an exception is raised instead, if the process is
        invalid (``ProcessValidationError``) or a service task has no handler
        (``HandlerNotFoundError``).
        """
        # load() has validated the process already. This catches a Process
        # built in code, which the runtime would otherwise run unchecked.
        validate(process)
        return run_process(process, self._handlers, variables)
