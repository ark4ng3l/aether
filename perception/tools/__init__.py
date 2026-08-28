"""
Tool auto-registration for AETHER perception layer.

Importing this package triggers registration of every available tool
into the global ``ToolRegistry``.
"""

from aether.perception.tools.registry import registry

# ── Always-available tools ──────────────────────────────────────────
from aether.perception.tools.search_tools import search_tools
registry.register(search_tools)

from aether.perception.tools.social_tools import social_tools
registry.register(social_tools)

from aether.perception.tools.subdomain_tools import subdomain_tools
registry.register(subdomain_tools)

from aether.perception.tools.geo_tools import geo_tools
registry.register(geo_tools)

from aether.perception.tools.breach_tools import breach_tools
registry.register(breach_tools)

# ── Optional tools (degrade gracefully) ─────────────────────────────
try:
    from aether.perception.tools.network_tools import network_tools
    registry.register(network_tools)
except ImportError:
    pass

try:
    from aether.perception.tools.metadata_tools import metadata_tools
    registry.register(metadata_tools)
except ImportError:
    pass

try:
    from aether.perception.crawler import crawler
    registry.register(crawler)
except ImportError:
    pass

try:
    from aether.perception.vlm_processor import vlm_processor
    registry.register(vlm_processor)
except ImportError:
    pass
