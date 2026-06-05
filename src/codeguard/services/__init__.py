"""Compatibility shim. The services package was renamed to application.

This shim is removed in a later commit once all imports have been migrated.
"""

from ..application import *  # noqa: F401,F403
from ..application import __all__  # noqa: F401
