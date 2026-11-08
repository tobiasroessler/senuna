"""Senuna: a lightweight BPMN 2.0 workflow engine for Python."""

# A folder with an __init__.py is a package; this file runs on the first
# "import senuna". The imports below re-export names from the submodules, so
# users write "from senuna import SenunaError" instead of
# "from senuna.exceptions import SenunaError".
from senuna.exceptions import (
    BpmnParseError,
    HandlerNotFoundError,
    ProcessValidationError,
    SenunaError,
)

# __all__ lists the public names of the package. It decides what
# "from senuna import *" imports, and mypy (strict) only accepts names listed
# here as exported: without it, "from senuna import SenunaError" is an error.
__all__ = [
    "BpmnParseError",
    "HandlerNotFoundError",
    "ProcessValidationError",
    "SenunaError",
]
