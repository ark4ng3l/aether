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

from aether.perception.tools.image_tools import image_tools
registry.register(image_tools)

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

# ── Phase 1 Expansion Tools ────────────────────────────────────────
try:
    from aether.perception.tools.whois_tools import whois_tools
    registry.register(whois_tools)
except ImportError:
    pass

try:
    from aether.perception.tools.shodan_tools import shodan_tools
    registry.register(shodan_tools)
except ImportError:
    pass

try:
    from aether.perception.tools.github_tools import github_dorker
    registry.register(github_dorker)
except ImportError:
    pass

# ── Phase 2 Expansion Tools ────────────────────────────────────────
try:
    from aether.perception.tools.company_tools import company_recon
    registry.register(company_recon)
except ImportError:
    pass

try:
    from aether.perception.tools.news_tools import news_intel
    registry.register(news_intel)
except ImportError:
    pass

try:
    from aether.perception.tools.threat_intel_tools import threat_intel
    registry.register(threat_intel)
except ImportError:
    pass

# ── Advanced Passive OSINT Suite (Phase 3) ─────────────────────────
try:
    from aether.perception.tools.wayback_tools import wayback_tool
    registry.register(wayback_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.favicon_tools import favicon_tool
    registry.register(favicon_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.tech_stack_tools import tech_stack_tool
    registry.register(tech_stack_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.typosquat_tools import typosquat_tool
    registry.register(typosquat_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.asn_tools import asn_tool
    registry.register(asn_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.ssl_tools import ssl_tool
    registry.register(ssl_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.bucket_tools import bucket_tool
    registry.register(bucket_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.sitemap_tools import robots_sitemap_tool
    registry.register(robots_sitemap_tool)
except ImportError:
    pass

# ── Extended Reconnaissance & Security Audit Suite (Phase 4) ────────
try:
    from aether.perception.tools.passive_dns_tools import passive_dns_tool
    registry.register(passive_dns_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.email_security_tools import email_security_tool
    registry.register(email_security_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.certstream_tools import cert_transparency_tool
    registry.register(cert_transparency_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.threat_reputation_tools import threat_reputation_tool
    registry.register(threat_reputation_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.port_prober_tools import port_prober_tool
    registry.register(port_prober_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.security_headers_tools import security_headers_tool
    registry.register(security_headers_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.api_schema_tools import api_schema_tool
    registry.register(api_schema_tool)
except ImportError:
    pass

# ── Persona & Human OSINT Suite (Phase 5) ───────────────────────────
try:
    from aether.perception.tools.email_oracle_tools import email_oracle_tool
    registry.register(email_oracle_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.phone_intel_tools import phone_intel_tool
    registry.register(phone_intel_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.deep_social_matrix_tools import deep_social_matrix_tool
    registry.register(deep_social_matrix_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.scholarly_tools import scholarly_intel_tool
    registry.register(scholarly_intel_tool)
except ImportError:
    pass

# ── Next-Gen Stealth & Dark Web Suite ──────────────────────────────
try:
    from aether.perception.tools.stealth_browser import StealthBrowserTool
    stealth_browser_tool = StealthBrowserTool()
    registry.register(stealth_browser_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.darkweb_tools import DarkWebReconTool
    darkweb_recon_tool = DarkWebReconTool()
    registry.register(darkweb_recon_tool)
except ImportError:
    pass

# ── OSINT Framework Complete Expansion Suite ───────────────────────
try:
    from aether.perception.tools.crypto_tools import crypto_tracer_tool
    registry.register(crypto_tracer_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.transport_tools import geo_transport_tool
    registry.register(geo_transport_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.sanctions_tools import sanctions_screener_tool
    registry.register(sanctions_screener_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.advanced_visual_tools import visual_forensics_tool
    registry.register(visual_forensics_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.paste_tools import paste_hunter_tool
    registry.register(paste_hunter_tool)
except ImportError:
    pass

try:
    from aether.perception.tools.reverse_whois_tools import reverse_whois_tool
    registry.register(reverse_whois_tool)
except ImportError:
    pass

# ── Forensic Reasoning & Behavioral Intelligence Suite ──────────────
try:
    from aether.perception.tools.intelligence_tools import (
        EntityResolutionTool,
        StylometryTool,
        TemporalRhythmTool,
    )
    registry.register(EntityResolutionTool())
    registry.register(StylometryTool())
    registry.register(TemporalRhythmTool())
except ImportError:
    pass

# ── Full-Spectrum OSINT & Cyber Infrastructure Expansion ────────────
try:
    import aether.perception.tools.social_matrix_tools
    import aether.perception.tools.web_check_suite
    import aether.perception.tools.geospatial_intelligence
except ImportError:
    pass

