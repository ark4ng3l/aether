"""
PipelineChainer — Autonomous Output-to-Input Tool & Entity Chaining for AETHER v4.0.
Maps discoveries from one perception tool (e.g. open ports, hostnames, IPs, hashes) into target parameters for downstream tools.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional
from aether.core.logger import logger
from aether.perception.tools.registry import BaseTool, ToolResult, registry


class PipelineChainer:
    """Coordinates multi-stage tool chains where output from stage N feeds stage N+1."""

    @staticmethod
    def extract_chainable_targets(tool_result_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extracts candidate IPs, domains, hashes, and ports from arbitrary tool result data.
        Returns:
            {"ips": [...], "domains": [...], "ports": [...], "emails": [...]}
        """
        raw_text = str(tool_result_data)
        
        # Regex extractors
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        domain_pattern = r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b"
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        ips = list(set(re.findall(ip_pattern, raw_text)))
        domains = list(set(re.findall(domain_pattern, raw_text)))
        emails = list(set(re.findall(email_pattern, raw_text)))

        # Clean noise domains
        noise_domains = {"example.com", "schema.org", "w3.org", "purl.org", "json-schema.org"}
        domains = [d for d in domains if d.lower() not in noise_domains and not d.endswith((".png", ".jpg", ".js", ".css"))]

        return {
            "ips": ips[:10],
            "domains": domains[:15],
            "emails": emails[:5],
        }

    async def execute_chain(
        self,
        initial_tool_name: str,
        initial_params: Dict[str, Any],
        subsequent_tool_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Executes a sequence of tools, automatically routing extracted entities as inputs.
        """
        chain_results: List[Dict[str, Any]] = []
        current_tool_name = initial_tool_name
        current_params = initial_params

        for next_tool_name in [initial_tool_name] + subsequent_tool_names:
            tool = registry.get_tool(next_tool_name)
            if not tool:
                logger.warning(f"Chainer: Tool '{next_tool_name}' not found in registry.")
                continue

            logger.info(f"PipelineChainer executing: {next_tool_name} with {current_params}")
            try:
                res: ToolResult = await tool.execute(**current_params)
                chain_results.append({
                    "tool": next_tool_name,
                    "params": current_params,
                    "success": res.success,
                    "data": res.data,
                    "error": res.error,
                })

                if not res.success:
                    logger.warning(f"PipelineChainer stopped on {next_tool_name} due to failure.")
                    break

                # Prepare inputs for the next tool in sequence
                targets = self.extract_chainable_targets(res.data if isinstance(res.data, dict) else {"data": res.data})
                
                # Determine best parameter for next tool
                if targets.get("ips"):
                    current_params = {"ip": targets["ips"][0], "target": targets["ips"][0], "query": targets["ips"][0]}
                elif targets.get("domains"):
                    current_params = {"domain": targets["domains"][0], "target": targets["domains"][0], "query": targets["domains"][0]}
                else:
                    break

            except Exception as exc:
                logger.error(f"PipelineChainer error on {next_tool_name}: {exc}")
                break

        return chain_results


pipeline_chainer = PipelineChainer()
