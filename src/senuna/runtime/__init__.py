"""Running processes: process instances, tokens, handler context and run().

The runtime knows the model, but not XML or the database.
"""

# Re-exported from the submodules, so users write
# "from senuna.runtime import run" instead of
# "from senuna.runtime.executor import run". See senuna/__init__.py for
# what __init__.py and __all__ do.
from senuna.runtime.context import ServiceTaskContext, ServiceTaskHandler
from senuna.runtime.executor import run
from senuna.runtime.instance import Failure, InstanceStatus, ProcessInstance, Token

__all__ = [
    "Failure",
    "InstanceStatus",
    "ProcessInstance",
    "ServiceTaskContext",
    "ServiceTaskHandler",
    "Token",
    "run",
]
