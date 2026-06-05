"""Compatibility shim. The persistence package moved to infrastructure.persistence.

This shim is removed in a later commit once all imports have been migrated.
"""

from ..infrastructure.persistence import *  # noqa: F401,F403
from ..infrastructure.persistence import __all__  # noqa: F401
