"""
NetworkTools — DNS reconnaissance with graceful dnspython fallback.
"""

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

try:
    import dns.asyncresolver
    _HAS_DNS = True
except ImportError:
    _HAS_DNS = False


class NetworkTools(BaseTool):
    """Performs DNS lookups (A, MX, TXT, NS, CNAME records)."""

    def __init__(self):
        super().__init__(
            name="network_recon",
            description="Performs comprehensive DNS lookups (A, AAAA, MX, TXT, NS, CNAME records).",
            category="DNS & Protocols",
            icon="lan",
            default_param_key="domain",
            example_input="cloudflare.com",
        )

    async def execute(self, domain: str = "", **kwargs) -> ToolResult:  # noqa: D401
        domain = domain or kwargs.get("query", "")
        if not domain:
            return ToolResult(success=False, data={}, error="No domain provided")

        if not _HAS_DNS:
            return ToolResult(
                success=False,
                data={},
                error="dnspython is not installed — run: pip install dnspython",
            )

        logger.info(f"Network recon on: {domain}")
        results: dict[str, list[str]] = {}

        resolver = dns.asyncresolver.Resolver()
        for rtype in ("A", "AAAA", "MX", "TXT", "NS", "CNAME"):
            try:
                answers = await resolver.resolve(domain, rtype)
                results[rtype] = [str(r) for r in answers]
            except Exception:
                results[rtype] = []

        return ToolResult(success=True, data=results)


network_tools = NetworkTools()
