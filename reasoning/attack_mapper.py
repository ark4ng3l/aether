"""
Automated MITRE ATT&CK & Threat Pathing Mapper.

Correlates discovered technical OSINT (open ports, tech stacks, CVEs, misconfigurations)
with the MITRE ATT&CK Enterprise Framework to synthesize actionable threat intelligence
and attack vector graphs.
"""

from __future__ import annotations

import uuid
from typing import Dict, Any, List, Optional
from aether.core.state import Entity, EntityType, RelationshipType
from aether.core.logger import logger


MITRE_TACTICS_MAPPING = {
    "T1190": {
        "id": "T1190",
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "description": "Adversaries may attempt to exploit vulnerabilities in Internet-facing software (web servers, APIs, web apps).",
        "triggers": ["http", "https", "cve", "apache", "nginx", "iis", "tomcat", "wordpress", "drupal", "joomla"],
    },
    "T1133": {
        "id": "T1133",
        "name": "External Remote Services",
        "tactic": "Initial Access & Persistence",
        "description": "Adversaries may leverage exposed remote services (RDP, SSH, VPN) to establish foothold.",
        "triggers": ["22/tcp", "ssh", "3389/tcp", "rdp", "5900/tcp", "vnc", "telnet", "vpn"],
    },
    "T1589": {
        "id": "T1589",
        "name": "Gather Victim Identity Information",
        "tactic": "Reconnaissance",
        "description": "Adversaries may gather identity information (emails, usernames, personas) to target credentials.",
        "triggers": ["email", "breach", "social_handle", "persona", "scholarly"],
    },
    "T1596": {
        "id": "T1596",
        "name": "Search Open Technical Databases",
        "tactic": "Reconnaissance",
        "description": "Adversaries search Certificate Transparency, DNS, WHOIS, and Shodan to map target network architecture.",
        "triggers": ["shodan", "cert_transparency", "whois", "passive_dns", "asn"],
    },
    "T1552": {
        "id": "T1552",
        "name": "Unsecured Credentials & Code Leaks",
        "tactic": "Credential Access",
        "description": "Adversaries search public repositories, cloud buckets, and paste sites for hardcoded secrets.",
        "triggers": ["github_dork", "bucket", "aws_s3", "pastebin", "secret"],
    },
    "T1584": {
        "id": "T1584",
        "name": "Compromise Infrastructure (Subdomain Takeover)",
        "tactic": "Resource Development",
        "description": "Adversaries identify dangling DNS pointers and typosquatting domains to impersonate or intercept traffic.",
        "triggers": ["typosquat", "cname", "dangling_dns", "s3_bucket"],
    },
}


class AttackMapper:
    """
    Synthesizes threat models and MITRE ATT&CK attack path vectors from discovered entities.
    """

    @classmethod
    def analyze_entities(cls, entities: List[Entity]) -> List[Dict[str, Any]]:
        """
        Scans all discovered entities in the investigation and maps them
        to matching MITRE ATT&CK techniques with risk scoring and confidence.
        """
        matched_techniques: Dict[str, Dict[str, Any]] = {}

        for entity in entities:
            # Combine entity properties and type for matching
            text_corpus = f"{entity.id} {entity.type.value} {str(entity.properties)}".lower()

            for tech_id, tech in MITRE_TACTICS_MAPPING.items():
                matching_triggers = [tr for tr in tech["triggers"] if tr in text_corpus]
                if matching_triggers:
                    if tech_id not in matched_techniques:
                        matched_techniques[tech_id] = {
                            "technique_id": tech_id,
                            "name": tech["name"],
                            "tactic": tech["tactic"],
                            "description": tech["description"],
                            "matched_triggers": list(set(matching_triggers)),
                            "supporting_entity_ids": [entity.id],
                            "risk_score": cls._calculate_risk(tech_id, matching_triggers),
                        }
                    else:
                        matched_techniques[tech_id]["matched_triggers"].extend(matching_triggers)
                        matched_techniques[tech_id]["matched_triggers"] = list(set(matched_techniques[tech_id]["matched_triggers"]))
                        if entity.id not in matched_techniques[tech_id]["supporting_entity_ids"]:
                            matched_techniques[tech_id]["supporting_entity_ids"].append(entity.id)

        # Sort by risk score descending
        results = sorted(matched_techniques.values(), key=lambda x: x["risk_score"], reverse=True)
        return results

    @classmethod
    def generate_attack_path_nodes(cls, matched_techniques: List[Dict[str, Any]], target_seed: str) -> List[Entity]:
        """
        Generates Graph entities representing MITRE ATT&CK tactics linked to the target.
        """
        nodes = []
        for tech in matched_techniques:
            node_id = f"mitre_{tech['technique_id'].lower()}_{uuid.uuid4().hex[:4]}"
            ent = Entity(
                id=node_id,
                type=EntityType.ATTACK_PATTERN if hasattr(EntityType, "ATTACK_PATTERN") else EntityType.ARTIFACT,
                confidence=min(1.0, 0.6 + len(tech["supporting_entity_ids"]) * 0.1),
                properties={
                    "name": f"[{tech['technique_id']}] {tech['name']}",
                    "label": f"MITRE: {tech['name']}",
                    "tactic": tech["tactic"],
                    "risk_score": tech["risk_score"],
                    "supporting_entities": tech["supporting_entity_ids"],
                    "description": tech["description"],
                    "framework": "MITRE ATT&CK Enterprise v14",
                },
            )
            nodes.append(ent)
        return nodes

    @staticmethod
    def _calculate_risk(tech_id: str, triggers: List[str]) -> float:
        """Calculates risk score (0.0 to 10.0) based on severity of indicators."""
        base_scores = {
            "T1190": 8.5,  # RCE / Web Exploits
            "T1133": 8.0,  # Remote admin ports
            "T1552": 7.5,  # Credential leaks
            "T1584": 6.5,  # Subdomain takeovers
            "T1589": 5.5,  # Identity info
            "T1596": 4.0,  # Passive reconnaissance
        }
        score = base_scores.get(tech_id, 5.0)
        # Bonus for multiple corroborating triggers
        score = min(10.0, score + (len(triggers) * 0.3))
        return round(score, 1)


attack_mapper = AttackMapper()
