"""The BPMN 2.0 model: plain, immutable data that matches the specification.

The model depends on nothing else in senuna.
"""

# Re-exported from the submodules, so users write
# "from senuna.model import Process" instead of
# "from senuna.model.process import Process". See senuna/__init__.py for
# what __init__.py and __all__ do.
from senuna.model.activities import Activity, ServiceTask, Task
from senuna.model.base import BaseElement, FlowElement, FlowNode
from senuna.model.events import EndEvent, Event, StartEvent
from senuna.model.process import Process
from senuna.model.sequence_flow import SequenceFlow

__all__ = [
    "Activity",
    "BaseElement",
    "EndEvent",
    "Event",
    "FlowElement",
    "FlowNode",
    "Process",
    "SequenceFlow",
    "ServiceTask",
    "StartEvent",
    "Task",
]
