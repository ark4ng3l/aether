"""
CyberFrameworks — MITRE ATT&CK v19.1, MITRE D3FEND v1.4, and MITRE Fight Fraud (F3 v1.1) Intelligence Engine.

Inspired by Anthropic-Cybersecurity-Skills repository.
Enables autonomous reasoning agents to tag, classify, and structure all forensic discoveries
and threat hypotheses against canonical international cybersecurity and fraud frameworks.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class FrameworkMapping(BaseModel):
    framework: str  # 'MITRE_ATTACK', 'MITRE_F3', 'MITRE_D3FEND', 'NIST_CSF'
    technique_id: str
    technique_name: str
    tactic: str
    confidence: float = 0.9
    evidence: str = ""


class CyberFrameworksEngine:
    """
    Cognitive mapping engine for ATT&CK v19.1, D3FEND, and Fight Fraud F3.
    """

    ATTACK_V19_TECHNIQUES: Dict[str, Dict[str, str]] = {
        # Reconnaissance (TA0043)
        "T1595": {"name": "Active Scanning", "tactic": "Reconnaissance"},
        "T1595.001": {"name": "Scanning IP Blocks", "tactic": "Reconnaissance"},
        "T1595.002": {"name": "Vulnerability Scanning", "tactic": "Reconnaissance"},
        "T1592": {"name": "Gather Victim Host Information", "tactic": "Reconnaissance"},
        "T1593": {"name": "Search Open Websites/Domains", "tactic": "Reconnaissance"},
        "T1593.001": {"name": "Social Media", "tactic": "Reconnaissance"},
        "T1593.002": {"name": "Search Engines", "tactic": "Reconnaissance"},
        "T1594": {"name": "Search Victim-Owned Websites", "tactic": "Reconnaissance"},
        "T1596": {"name": "Search Open Technical Databases", "tactic": "Reconnaissance"},
        "T1596.001": {"name": "DNS/Passive DNS", "tactic": "Reconnaissance"},
        "T1596.002": {"name": "WHOIS", "tactic": "Reconnaissance"},
        "T1596.003": {"name": "Digital Certificates", "tactic": "Reconnaissance"},
        "T1596.004": {"name": "CDNs", "tactic": "Reconnaissance"},
        "T1596.005": {"name": "Scan Databases (Shodan/Censys)", "tactic": "Reconnaissance"},
        "T1589": {"name": "Gather Victim Identity Information", "tactic": "Reconnaissance"},
        "T1589.001": {"name": "Credentials", "tactic": "Reconnaissance"},
        "T1589.002": {"name": "Email Addresses", "tactic": "Reconnaissance"},
        "T1589.003": {"name": "Employee Names", "tactic": "Reconnaissance"},
        "T1590": {"name": "Gather Victim Network Information", "tactic": "Reconnaissance"},
        "T1590.001": {"name": "Domain Properties", "tactic": "Reconnaissance"},
        "T1590.002": {"name": "DNS", "tactic": "Reconnaissance"},
        "T1590.005": {"name": "IP Addresses", "tactic": "Reconnaissance"},
        # Resource Development (TA0042)
        "T1583": {"name": "Acquire Infrastructure", "tactic": "Resource Development"},
        "T1583.001": {"name": "Domains", "tactic": "Resource Development"},
        "T1584": {"name": "Compromise Infrastructure", "tactic": "Resource Development"},
        "T1585": {"name": "Establish Accounts", "tactic": "Resource Development"},
        "T1585.001": {"name": "Social Media Accounts", "tactic": "Resource Development"},
        "T1585.002": {"name": "Email Accounts", "tactic": "Resource Development"},
        # Stealth / Defense Evasion (TA0005)
        "T1070": {"name": "Indicator Removal", "tactic": "Stealth"},
        "T1090": {"name": "Proxy Routing", "tactic": "Stealth"},
        "T1090.003": {"name": "Multi-hop Proxy / Tor", "tactic": "Stealth"},
        "T1562": {"name": "Impair Defenses", "tactic": "Defense Impairment"},
    }

    F3_FRAUD_TECHNIQUES: Dict[str, Dict[str, str]] = {
        # Positioning (FA0001)
        "F1001": {"name": "Synthetic Identity Seeding", "tactic": "Positioning"},
        "F1002": {"name": "Account Warming & Persona Maturation", "tactic": "Positioning"},
        "F1003": {"name": "SIM-Swap Pre-Positioning", "tactic": "Positioning"},
        "F1005": {"name": "Add Unauthorized Beneficiary", "tactic": "Positioning"},
        "F1007": {"name": "Adversary-in-the-Browser (AitB)", "tactic": "Positioning"},
        "F1008": {"name": "Banking Session Hijack", "tactic": "Positioning"},
        # Monetization (FA0002)
        "F1020": {"name": "Money Mule Layering", "tactic": "Monetization"},
        "F1021": {"name": "Crypto Off-Ramping & Tumbling", "tactic": "Monetization"},
        "F1022": {"name": "Authorized Push Payment (APP) Fraud", "tactic": "Monetization"},
        "F1025": {"name": "Fraudulent Wire Transfer", "tactic": "Monetization"},
        "F1026": {"name": "Card Cash-Out Scheme", "tactic": "Monetization"},
        "F1028": {"name": "Refund & Chargeback Exploitation", "tactic": "Monetization"},
    }

    D3FEND_COUNTERMEASURES: Dict[str, Dict[str, str]] = {
        "D3-NTA": {"name": "Network Traffic Analysis", "target": "T1090"},
        "D3-DNSA": {"name": "DNS Analysis & Filtering", "target": "T1590.002"},
        "D3-SPFA": {"name": "Sender Policy Framework Verification", "target": "T1589.002"},
        "D3-SCA": {"name": "Subdomain & Certificate Auditing", "target": "T1596.003"},
        "D3-DCA": {"name": "Digital Certificate Validation", "target": "T1596.003"},
        "D3-ARA": {"name": "Account Registration Auditing", "target": "F1001"},
        "D3-MTA": {"name": "Money Movement Anomaly Detection", "target": "F1020"},
    }

    ATLAS_AI_TECHNIQUES: Dict[str, Dict[str, str]] = {
        "AML.T0051": {"name": "LLM Prompt Injection", "tactic": "Initial Access & Execution"},
        "AML.T0051.000": {"name": "Direct Prompt Injection / Jailbreak", "tactic": "Execution"},
        "AML.T0051.001": {"name": "Indirect Prompt Injection via Web Content", "tactic": "Execution"},
        "AML.T0018": {"name": "Backdoor / Training Data Poisoning", "tactic": "Persistence"},
        "AML.T0015": {"name": "Adversarial Model Evasion", "tactic": "Defense Evasion"},
        "AML.T0040": {"name": "ML Model Extraction & Weight Scraping", "tactic": "Exfiltration"},
        "AML.T0043": {"name": "Adversarial Context & RAG Manipulation", "tactic": "Execution"},
        "AML.T0024": {"name": "Insecure Output Handling", "tactic": "Impact"},
    }

    NIST_CSF2_FUNCTIONS: Dict[str, Dict[str, str]] = {
        "GV": {"name": "Govern", "desc": "Organizational context, risk strategy, policy"},
        "ID": {"name": "Identify", "desc": "Asset management, vulnerability discovery, risk assessment"},
        "PR": {"name": "Protect", "desc": "Access control, data security, platform defense"},
        "DE": {"name": "Detect", "desc": "Anomalies, events, continuous monitoring"},
        "RS": {"name": "Respond", "desc": "Incident management, analysis, mitigation"},
        "RC": {"name": "Recover", "desc": "Restoration, operational resilience, post-incident review"},
    }

    @classmethod
    def map_findings(cls, findings_summary: str, discovered_types: Optional[List[str]] = None) -> List[FrameworkMapping]:
        """
        Cognitively maps text findings and entities to MITRE ATT&CK, ATLAS, D3FEND, and F3 techniques.
        """
        mappings: List[FrameworkMapping] = []
        text = findings_summary.lower()
        types = [t.lower() for t in (discovered_types or [])]

        # Reconnaissance mapping
        if "subdomain" in text or "domain" in types:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATTACK",
                technique_id="T1590.001",
                technique_name=cls.ATTACK_V19_TECHNIQUES["T1590.001"]["name"],
                tactic="Reconnaissance",
                evidence="Domain and DNS topology enumeration discovered.",
            ))
            mappings.append(FrameworkMapping(
                framework="MITRE_D3FEND",
                technique_id="D3-DNSA",
                technique_name=cls.D3FEND_COUNTERMEASURES["D3-DNSA"]["name"],
                tactic="Defensive Countermeasure",
                evidence="Implement DNS monitoring and query logging.",
            ))

        if "certificate" in text or "ssl" in text or "tls" in text:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATTACK",
                technique_id="T1596.003",
                technique_name=cls.ATTACK_V19_TECHNIQUES["T1596.003"]["name"],
                tactic="Reconnaissance",
                evidence="X.509 Certificate Transparency and SAN enumeration.",
            ))

        if "social" in text or "username" in text or "profile" in text or "handle" in types:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATTACK",
                technique_id="T1593.001",
                technique_name=cls.ATTACK_V19_TECHNIQUES["T1593.001"]["name"],
                tactic="Reconnaissance",
                evidence="Cross-platform social media persona and handle correlation.",
            ))

        if "email" in text or "email" in types:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATTACK",
                technique_id="T1589.002",
                technique_name=cls.ATTACK_V19_TECHNIQUES["T1589.002"]["name"],
                tactic="Reconnaissance",
                evidence="Harvested organizational email patterns and mailbox infrastructure.",
            ))
            mappings.append(FrameworkMapping(
                framework="MITRE_D3FEND",
                technique_id="D3-SPFA",
                technique_name=cls.D3FEND_COUNTERMEASURES["D3-SPFA"]["name"],
                tactic="Defensive Countermeasure",
                evidence="Enforce strict DMARC reject policies and SPF records.",
            ))

        if "tor" in text or "proxy" in text:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATTACK",
                technique_id="T1090.003",
                technique_name=cls.ATTACK_V19_TECHNIQUES["T1090.003"]["name"],
                tactic="Stealth",
                evidence="Traffic routed via encrypted multi-hop Tor onion circuits.",
            ))

        # Financial Fraud (F3) mapping
        if "crypto" in text or "wallet" in text or "mule" in text or "layering" in text:
            mappings.append(FrameworkMapping(
                framework="MITRE_F3",
                technique_id="F1021",
                technique_name=cls.F3_FRAUD_TECHNIQUES["F1021"]["name"],
                tactic="Monetization",
                evidence="Cryptocurrency wallet cluster or transaction flow identified.",
            ))
            mappings.append(FrameworkMapping(
                framework="MITRE_D3FEND",
                technique_id="D3-MTA",
                technique_name=cls.D3FEND_COUNTERMEASURES["D3-MTA"]["name"],
                tactic="Defensive Countermeasure",
                evidence="Deploy blockchain heuristic monitoring and AML screening.",
            ))

        if "synthetic" in text or "identity" in text or "persona" in text:
            mappings.append(FrameworkMapping(
                framework="MITRE_F3",
                technique_id="F1001",
                technique_name=cls.F3_FRAUD_TECHNIQUES["F1001"]["name"],
                tactic="Positioning",
                evidence="Synthetic persona fabrication or identity resolution match.",
            ))

        # AI & LLM Threat vectors (MITRE ATLAS)
        if "prompt" in text or "injection" in text or "jailbreak" in text or "llm" in text:
            mappings.append(FrameworkMapping(
                framework="MITRE_ATLAS",
                technique_id="AML.T0051",
                technique_name=cls.ATLAS_AI_TECHNIQUES["AML.T0051"]["name"],
                tactic="Execution",
                evidence="Prompt injection or adversarial LLM input heuristic identified.",
            ))

        return mappings

    @classmethod
    def get_matrix_summary(cls) -> Dict[str, Any]:
        """Returns catalogue of supported framework versions and technique counts."""
        return {
            "frameworks": [
                {
                    "name": "MITRE ATT&CK",
                    "version": "v19.1 (2026)",
                    "techniques_count": len(cls.ATTACK_V19_TECHNIQUES),
                    "scope": "Adversary TTPs & Stealth Evasion",
                },
                {
                    "name": "MITRE Fight Fraud (F3)",
                    "version": "v1.1 (2026)",
                    "techniques_count": len(cls.F3_FRAUD_TECHNIQUES),
                    "scope": "Positioning & Monetization Cyber-Fraud",
                },
                {
                    "name": "MITRE D3FEND",
                    "version": "v1.4.0",
                    "techniques_count": len(cls.D3FEND_COUNTERMEASURES),
                    "scope": "Defensive Countermeasures & Hardening",
                },
                {
                    "name": "MITRE ATLAS",
                    "version": "v4.0 (2026)",
                    "techniques_count": len(cls.ATLAS_AI_TECHNIQUES),
                    "scope": "Adversarial Threat Landscape for AI & LLM Systems",
                },
                {
                    "name": "NIST CSF",
                    "version": "2.0",
                    "techniques_count": len(cls.NIST_CSF2_FUNCTIONS),
                    "scope": "Govern, Identify, Protect, Detect, Respond, Recover",
                },
            ],
            "total_supported_techniques": (
                len(cls.ATTACK_V19_TECHNIQUES)
                + len(cls.F3_FRAUD_TECHNIQUES)
                + len(cls.D3FEND_COUNTERMEASURES)
                + len(cls.ATLAS_AI_TECHNIQUES)
                + len(cls.NIST_CSF2_FUNCTIONS)
            ),
        }


cyber_frameworks = CyberFrameworksEngine()
