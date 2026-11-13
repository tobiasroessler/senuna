"""Senuna: a lightweight BPMN 2.0 workflow engine for Python."""

# A folder with an __init__.py is a package; this file runs on the first
# "import senuna". The imports below re-export names from the submodules, so
# users write "from senuna import Senuna" instead of
# "from senuna.engine import Senuna".
from senuna.engine import Senuna
from senuna.exceptions import (
    BpmnParseError,
    HandlerAlreadyRegisteredError,
    HandlerNotFoundError,
    ProcessValidationError,
    SenunaError,
)
from senuna.runtime import ServiceTaskContext

# __all__ lists the public names of the package. It decides what
# "from senuna import *" imports, and mypy (strict) only accepts names listed
# here as exported: without it, "from senuna import Senuna" is an error.
__all__ = [
    "BpmnParseError",
    "HandlerAlreadyRegisteredError",
    "HandlerNotFoundError",
    "ProcessValidationError",
    "Senuna",
    "SenunaError",
    "ServiceTaskContext",
]
