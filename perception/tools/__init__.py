"""
Tool auto-registration for AETHER perception layer.

Importing this package triggers registration of every available tool
into the global ``ToolRegistry``.  Missing optional dependencies
(dnspython, Pillow, playwright) are handled gracefully.
"""

from aether.perception.tools.registry import registry

# ── Always-available tools ──────────────────────────────────────────
from aether.perception.tools.search_tools import search_tools    # noqa: F401
registry.register(search_tools)

from aether.perception.tools.social_tools import social_tools    # noqa: F401
registry.register(social_tools)

# ── Optional tools (degrade gracefully) ─────────────────────────────
try:
    from aether.perception.tools.network_tools import network_tools  # noqa: F401
    registry.register(network_tools)
except ImportError:
    pass

try:
    from aether.perception.tools.metadata_tools import metadata_tools  # noqa: F401
    registry.register(metadata_tools)
except ImportError:
    pass

try:
    from aether.perception.crawler import crawler  # noqa: F401
    registry.register(crawler)
except ImportError:
    pass

try:
    from aether.perception.vlm_processor import vlm_processor  # noqa: F401
    registry.register(vlm_processor)
except ImportError:
    pass
