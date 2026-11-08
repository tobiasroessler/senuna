"""Fixtures shared by all tests.

pytest loads this file automatically; the name conftest.py is fixed. Its
fixtures are available to every test in this folder without importing: a test
asks for one by naming it as a parameter, e.g.
``def test_x(hello_process: Process)``, and gets a fresh result each time.
"""

import pytest

from senuna.model import EndEvent, Process, SequenceFlow, ServiceTask, StartEvent


@pytest.fixture
def hello_process() -> Process:
    """start -> greet -> end: the same process as tests/bpmn/hello.bpmn."""
    return Process(
        id="hello",
        flow_elements=(
            StartEvent(id="start"),
            SequenceFlow(id="flow1", source_ref="start", target_ref="greet"),
            ServiceTask(id="greet", name="Greet"),
            SequenceFlow(id="flow2", source_ref="greet", target_ref="end"),
            EndEvent(id="end"),
        ),
    )
