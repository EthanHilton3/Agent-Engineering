from .edit import EDIT_TOOLS
from .files import READ_TOOLS, WRITE_TOOLS
from .git import GIT_TOOLS
from .registry import ToolRegistry
from .shell import SHELL_TOOLS


def build_registry() -> ToolRegistry:
    """The nine v3 tools, in a fixed order (the tool list must never change within a session)."""
    return ToolRegistry([*READ_TOOLS, *EDIT_TOOLS, *WRITE_TOOLS, *SHELL_TOOLS, *GIT_TOOLS])
