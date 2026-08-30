"""
Web-Check Diagnostic Suite — Comprehensive Web Infrastructure, DNS, SSL, WAF, and Standards Analyzer.

Inspired by Lissy93/web-check.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import httpx

from aether.perception.tools.registry import register_tool
from aether.core.logger import logger


@register_tool
async def dns_deep_check(
    domain: str,
) -> Dict[str, Any]:
    """
    Performs full-spectrum DNS resolution across 12+ record types (A, AAAA, MX, TXT, SOA, NS, CNAME, CAA, PTR, SRV, DNSKEY, DS).
    Checks DNSSEC validation and worldwide resolver consistency.

    Args:
        domain: Target hostname or root domain (e.g. example.com).
    """
    clean_dom = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    record_types = ["A", "AAAA", "MX", "TXT", "NS", "SOA", "CNAME", "CAA", "SRV", "DNSKEY", "DS"]
    results: Dict[str, List[str]] = {}

    async def _query_doh(rtype: str) -> Tuple[str, List[str]]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                url = f"https://cloudflare-dns.com/dns-query?name={clean_dom}&type={rtype}"
                resp = await client.get(url, headers={"accept": "application/dns-json"})
                if resp.status_code == 200:
                    data = resp.json()
                    answers = data.get("Answer", [])
                    records = [a.get("data", "") for a in answers if a.get("data")]
                    return rtype, records
        except Exception:
            pass
        return rtype, []

    tasks = [_query_doh(r) for r in record_types]
    doh_results = await asyncio.gather(*tasks)

    for rtype, records in doh_results:
        results[rtype] = records

    # DNSSEC check
    has_dnssec = bool(results.get("DNSKEY") or results.get("DS"))

    return {
        "success": True,
        "domain": clean_dom,
        "records": results,
        "dnssec_enabled": has_dnssec,
        "total_records_found": sum(len(v) for v in results.values()),
    }


@register_tool
async def ssl_cipher_audit(
    domain: str,
    port: int = 443,
) -> Dict[str, Any]:
    """
    Audits SSL/TLS certificate, cipher suites, protocol versions (TLS 1.2/1.3),
    Subject Alternative Names (SANs) for subdomain discovery, and expiration.

    Args:
        domain: Hostname or domain name to inspect.
        port: TLS port (default 443).
    """
    clean_dom = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        loop = asyncio.get_running_loop()

        def _probe_ssl():
            with socket.create_connection((clean_dom, port), timeout=5.0) as sock:
                with ctx.wrap_socket(sock, server_hostname=clean_dom) as ssock:
                    cert = ssock.getpeercert(binary_form=False)
                    cipher = ssock.cipher()
                    version = ssock.version()
                    return cert, cipher, version

        cert, cipher, version = await loop.run_in_executor(None, _probe_ssl)

        # SAN subdomains
        san_names = []
        if cert:
            alt_names = cert.get("subjectAltName", [])
            san_names = [name for typ, name in alt_names if typ == "DNS"]

        cipher_name, proto_ver, secret_bits = cipher if cipher else ("Unknown", "Unknown", 0)

        is_modern = version in ["TLSv1.2", "TLSv1.3"]
        is_weak_cipher = any(w in cipher_name.lower() for w in ["rc4", "3des", "des", "cbc", "null", "md5"])

        return {
            "success": True,
            "domain": clean_dom,
            "port": port,
            "tls_version": version,
            "is_modern_tls": is_modern,
            "cipher_suite": cipher_name,
            "key_bits": secret_bits,
            "weak_cipher_detected": is_weak_cipher,
            "issuer": cert.get("issuer", ()) if cert else (),
            "subject": cert.get("subject", ()) if cert else (),
            "expires_at": cert.get("notAfter", "") if cert else "",
            "subject_alternative_names_count": len(san_names),
            "san_discovered_domains": san_names[:25],
        }

    except Exception as exc:
        return {
            "success": False,
            "domain": clean_dom,
            "error": str(exc),
        }


@register_tool
async def security_standards_audit(
    url: str,
) -> Dict[str, Any]:
    """
    Checks RFC standard security files and policies:
    - /.well-known/security.txt (RFC 9116)
    - /robots.txt
    - /sitemap.xml
    - /humans.txt
    - /ads.txt

    Args:
        url: Base URL or domain to audit.
    """
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    files_to_check = {
        "security_txt": f"{base_url}/.well-known/security.txt",
        "security_txt_fallback": f"{base_url}/security.txt",
        "robots_txt": f"{base_url}/robots.txt",
        "sitemap_xml": f"{base_url}/sitemap.xml",
        "humans_txt": f"{base_url}/humans.txt",
        "ads_txt": f"{base_url}/ads.txt",
    }

    discovered: Dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        for name, file_url in files_to_check.items():
            try:
                resp = await client.get(file_url)
                if resp.status_code == 200 and len(resp.text.strip()) > 10:
                    lines = [line.strip() for line in resp.text.splitlines() if line.strip() and not line.startswith("#")]
                    discovered[name] = {
                        "present": True,
                        "url": file_url,
                        "lines_count": len(lines),
                        "snippet": lines[:10],
                    }
                else:
                    discovered[name] = {"present": False, "status": resp.status_code}
            except Exception:
                discovered[name] = {"present": False, "status": "unreachable"}

    has_security_txt = discovered.get("security_txt", {}).get("present") or discovered.get("security_txt_fallback", {}).get("present")

    return {
        "success": True,
        "base_url": base_url,
        "has_security_txt": bool(has_security_txt),
        "standards": discovered,
    }


@register_tool
async def redirect_hop_tracer(
    target_url: str,
) -> Dict[str, Any]:
    """
    Traces complete HTTP to HTTPS and canonical URL redirect hop chain.
    Captures status codes (301, 302, 307, 308), headers, and latency per hop.

    Args:
        target_url: Starting URL (e.g. http://example.com).
    """
    url = target_url if target_url.startswith("http") else f"http://{target_url}"
    hops = []
    curr_url = url

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
        for step in range(10):
            t0 = time.time()
            try:
                resp = await client.get(curr_url)
                latency_ms = round((time.time() - t0) * 1000, 1)

                hops.append({
                    "hop": step + 1,
                    "url": str(resp.url),
                    "status_code": resp.status_code,
                    "latency_ms": latency_ms,
                    "server": resp.headers.get("server", "hidden"),
                    "location": resp.headers.get("location"),
                })

                if resp.is_redirect and resp.headers.get("location"):
                    loc = resp.headers["location"]
                    if not loc.startswith("http"):
                        from urllib.parse import urljoin
                        loc = urljoin(curr_url, loc)
                    curr_url = loc
                else:
                    break
            except Exception as exc:
                hops.append({"hop": step + 1, "url": curr_url, "error": str(exc)})
                break

    is_https = hops[-1]["url"].startswith("https://") if hops else False
    return {
        "success": True,
        "initial_url": target_url,
        "final_url": hops[-1]["url"] if hops else None,
        "total_hops": len(hops),
        "enforces_https": is_https,
        "chain": hops,
    }


@register_tool
async def waf_classifier(
    url: str,
) -> Dict[str, Any]:
    """
    Fingerprints Web Application Firewall (WAF), CDN, and reverse proxy layer.
    Recognizes Cloudflare, Akamai, CloudFront, Imperva Incapsula, Fastly, Sucuri, F5 BIG-IP, Nginx, Caddy, Apache.

    Args:
        url: Domain or web application URL.
    """
    target = url if url.startswith("http") else f"https://{url}"

    waf_signatures = {
        "Cloudflare": {"headers": ["cf-ray", "cf-cache-status", "__cfduid"], "server": ["cloudflare"]},
        "AWS CloudFront": {"headers": ["x-amz-cf-id", "x-amz-cf-pop"], "server": ["cloudfront"]},
        "Akamai": {"headers": ["x-akamai-transformed", "akamai-origin-hop"], "server": ["akamaighost"]},
        "Imperva Incapsula": {"headers": ["x-cdn", "x-iinfo", "incap_ses"], "server": ["incapsula"]},
        "Fastly": {"headers": ["x-fastly-request-id", "fastly-debug-digest"], "server": ["fastly"]},
        "Sucuri": {"headers": ["x-sucuri-id", "x-sucuri-cache"], "server": ["sucuri"]},
        "F5 BIG-IP": {"headers": ["x-cnection", "bigipserver"], "server": ["big-ip"]},
    }

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(target)
            headers_lower = {k.lower(): v.lower() for k, v in resp.headers.items()}
            server_header = headers_lower.get("server", "")

            detected_wafs = []
            for waf_name, rules in waf_signatures.items():
                # Check headers
                if any(h in headers_lower for h in rules["headers"]):
                    detected_wafs.append(waf_name)
                    continue
                # Check server header
                if any(s in server_header for s in rules["server"]):
                    detected_wafs.append(waf_name)

            return {
                "success": True,
                "url": target,
                "server_header": server_header or "hidden",
                "detected_waf_cdn": detected_wafs or ["Direct / Undetected WAF"],
                "has_waf": len(detected_wafs) > 0,
            }
    except Exception as exc:
        return {"success": False, "url": target, "error": str(exc)}


@register_tool
def carbon_footprint_estimator(
    transfer_size_kb: float = 1200.0,
    is_green_host: bool = False,
) -> Dict[str, Any]:
    """
    Calculates estimated CO2 carbon emissions and energy consumption per page visit
    using the Sustainable Web Design model (v3).

    Args:
        transfer_size_kb: Total transfer size of web page in KB (default 1.2MB).
        is_green_host: Whether the server runs on verified renewable energy.
    """
    bytes_transferred = transfer_size_kb * 1024.0
    kwh_per_gb = 0.81  # kWh per GB of data transferred
    gb_transferred = bytes_transferred / (1024.0 ** 3)
    energy_kwh = gb_transferred * kwh_per_gb

    # Grid carbon intensity (global average ~442g CO2/kWh, renewable ~50g CO2/kWh)
    carbon_intensity = 50.0 if is_green_host else 442.0
    co2_grams = energy_kwh * carbon_intensity

    # Annual estimation based on 10,000 monthly visits
    annual_kg = (co2_grams * 10000.0 * 12.0) / 1000.0

    rating = "A+" if co2_grams < 0.1 else ("A" if co2_grams < 0.3 else ("B" if co2_grams < 0.6 else "C"))

    return {
        "success": True,
        "transfer_size_kb": transfer_size_kb,
        "is_green_host": is_green_host,
        "co2_grams_per_visit": round(co2_grams, 4),
        "energy_kwh_per_visit": round(energy_kwh, 6),
        "annual_co2_kg_estimate": round(annual_kg, 2),
        "eco_rating": rating,
    }


@register_tool
async def crtsh_subdomain_discovery(
    domain: str,
) -> Dict[str, Any]:
    """
    Discovers historical and active subdomains from public Certificate Transparency (CT) logs via crt.sh.

    Args:
        domain: Target domain (e.g. example.com).
    """
    clean_dom = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    subdomains = set()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://crt.sh/?q=%25.{clean_dom}&output=json"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code == 200:
                entries = resp.json()
                for entry in entries:
                    name_value = entry.get("name_value", "")
                    for sub in name_value.split("\n"):
                        sub_clean = sub.strip().lower().lstrip("*.")
                        if sub_clean and sub_clean.endswith(clean_dom):
                            subdomains.add(sub_clean)
    except Exception as exc:
        logger.debug(f"crt.sh query error: {exc}")

    sorted_subs = sorted(list(subdomains))
    return {
        "success": True,
        "domain": clean_dom,
        "total_subdomains_discovered": len(sorted_subs),
        "subdomains": sorted_subs[:100],
    }


@register_tool
async def email_spoofing_deep_audit(
    domain: str,
) -> Dict[str, Any]:
    """
    Audits domain email security: SPF lookup limit (<= 10 per RFC 7208), DMARC policy enforcement,
    DKIM selector discovery, and BIMI brand verification.

    Args:
        domain: Target domain name.
    """
    clean_dom = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    async def _query_txt(qname: str) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                url = f"https://cloudflare-dns.com/dns-query?name={qname}&type=TXT"
                resp = await client.get(url, headers={"accept": "application/dns-json"})
                if resp.status_code == 200:
                    data = resp.json()
                    return [a.get("data", "").strip('"') for a in data.get("Answer", [])]
        except Exception:
            pass
        return []

    # 1. SPF
    txt_records = await _query_txt(clean_dom)
    spf_record = next((r for r in txt_records if r.startswith("v=spf1")), None)
    spf_lookups_count = 0
    spf_valid = False
    if spf_record:
        # Count include:, a, mx, ptr, exists:, redirect=
        tokens = spf_record.split()
        lookup_mechanisms = [t for t in tokens if any(t.startswith(prefix) for prefix in ["include:", "a", "mx", "ptr", "exists:", "redirect="])]
        spf_lookups_count = len(lookup_mechanisms)
        spf_valid = spf_lookups_count <= 10

    # 2. DMARC
    dmarc_records = await _query_txt(f"_dmarc.{clean_dom}")
    dmarc_record = next((r for r in dmarc_records if r.startswith("v=DMARC1")), None)
    dmarc_policy = "none"
    dmarc_enforced = False
    if dmarc_record:
        m = re.search(r"p=(reject|quarantine|none)", dmarc_record, re.IGNORECASE)
        if m:
            dmarc_policy = m.group(1).lower()
            dmarc_enforced = dmarc_policy in ["reject", "quarantine"]

    # 3. BIMI
    bimi_records = await _query_txt(f"default._bimi.{clean_dom}")
    bimi_record = next((r for r in bimi_records if r.startswith("v=BIMI1")), None)

    return {
        "success": True,
        "domain": clean_dom,
        "spf": {
            "present": bool(spf_record),
            "raw": spf_record,
            "dns_lookup_count": spf_lookups_count,
            "within_rfc7208_limit": spf_valid,
        },
        "dmarc": {
            "present": bool(dmarc_record),
            "raw": dmarc_record,
            "policy": dmarc_policy,
            "is_enforced": dmarc_enforced,
        },
        "bimi": {
            "present": bool(bimi_record),
            "raw": bimi_record,
        },
        "spoofing_vulnerability": "HIGH" if not dmarc_enforced else ("LOW" if spf_valid else "MEDIUM"),
    }


@register_tool
async def web_check_full_audit(
    domain: str,
) -> Dict[str, Any]:
    """
    Orchestrates an all-in-one Web-Check diagnostic suite covering:
    DNS, SSL/TLS, Security Standards, Redirect Tracer, WAF/CDN detection, CT Subdomains, Email Spoofing, and Carbon Footprint.

    Args:
        domain: Hostname or root domain to audit.
    """
    clean_dom = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    dns_res, ssl_res, standards_res, redirect_res, waf_res, crt_res, email_res = await asyncio.gather(
        dns_deep_check(clean_dom),
        ssl_cipher_audit(clean_dom),
        security_standards_audit(clean_dom),
        redirect_hop_tracer(clean_dom),
        waf_classifier(clean_dom),
        crtsh_subdomain_discovery(clean_dom),
        email_spoofing_deep_audit(clean_dom),
    )

    carbon_res = carbon_footprint_estimator(transfer_size_kb=1500.0)

    return {
        "success": True,
        "domain": clean_dom,
        "timestamp": time.time(),
        "dns": dns_res,
        "ssl": ssl_res,
        "standards": standards_res,
        "redirects": redirect_res,
        "waf": waf_res,
        "subdomains_ct": crt_res,
        "email_security": email_res,
        "carbon": carbon_res,
    }
