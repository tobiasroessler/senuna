"""Tests for the exceptions senuna raises."""

import pickle

import pytest

from senuna import (
    BpmnParseError,
    HandlerNotFoundError,
    ProcessValidationError,
    SenunaError,
)


def test_senuna_error_is_an_exception() -> None:
    assert issubclass(SenunaError, Exception)


# parametrize runs the test once per class in the list, passed as error_class.
@pytest.mark.parametrize(
    "error_class", [BpmnParseError, ProcessValidationError, HandlerNotFoundError]
)
def test_every_error_derives_from_senuna_error(error_class: type[Exception]) -> None:
    assert issubclass(error_class, SenunaError)


def test_process_validation_error_lists_every_problem() -> None:
    error = ProcessValidationError("order", ["No StartEvent", "No EndEvent"])

    assert error.process_id == "order"
    assert error.problems == ("No StartEvent", "No EndEvent")
    assert str(error) == "Process 'order' is invalid:\n- No StartEvent\n- No EndEvent"


# pickle turns an object into bytes and back. That's what happens when an
# exception is passed between processes, e.g. from a background worker.
def test_process_validation_error_survives_pickling() -> None:
    original = ProcessValidationError("order", ["No StartEvent"])
    error = pickle.loads(pickle.dumps(original))

    assert error.process_id == "order"
    assert error.problems == ("No StartEvent",)
    assert str(error) == str(original)


def test_handler_not_found_error_names_the_task() -> None:
    error = HandlerNotFoundError("greet")

    assert error.task_id == "greet"
    assert str(error) == "No handler registered for service task 'greet'"


def test_handler_not_found_error_survives_pickling() -> None:
    error = pickle.loads(pickle.dumps(HandlerNotFoundError("greet")))

    assert error.task_id == "greet"
    assert str(error) == "No handler registered for service task 'greet'"
