"""
API Schema & GraphQL Introspection Inspector Tool for AETHER.
Discovers and inspects publicly exposed OpenAPI/Swagger documentation and GraphQL schemas.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

COMMON_SCHEMA_PATHS = [
    "/swagger.json",
    "/openapi.json",
    "/v2/api-docs",
    "/v3/api-docs",
    "/api/swagger.json",
    "/api/openapi.json",
    "/api/v1/swagger.json",
    "/swagger/v1/swagger.json",
    "/docs/swagger.json",
]

COMMON_GRAPHQL_PATHS = [
    "/graphql",
    "/api/graphql",
    "/v1/graphql",
    "/query",
]

GRAPHQL_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name
      kind
      description
    }
  }
}
"""


class APISchemaTool(BaseTool):
    """Discovers exposed OpenAPI/Swagger definitions and GraphQL schemas for API reconnaissance."""

    def __init__(self):
        super().__init__(
            name="api_schema_inspector",
            description="Discovers and inspects exposed OpenAPI/Swagger JSON API documentation and GraphQL Introspection schemas on target servers.",
            category="Recon",
            icon="Code",
            default_param_key="url",
            example_input="https://example.com",
            params={
                "url": "Target base URL or domain (e.g. https://api.example.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        raw_url = kwargs.get("url") or kwargs.get("domain") or kwargs.get("hostname") or kwargs.get("query") or ""
        raw_url = str(raw_url).strip()
        if not raw_url.startswith(("http://", "https://")):
            base_url = f"https://{raw_url}"
        else:
            base_url = raw_url.rstrip("/")

        logger.info(f"Inspecting API documentation and GraphQL schemas for: {base_url}")

        discovered_schemas: List[Dict[str, Any]] = []
        graphql_endpoints: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, verify=False) as client:
            # 1. Probe common OpenAPI / Swagger paths
            for path in COMMON_SCHEMA_PATHS:
                target_endpoint = f"{base_url}{path}"
                try:
                    res = await client.get(target_endpoint, headers={"User-Agent": "AETHER-APISchemaInspector/1.0"})
                    if res.status_code == 200 and "application/json" in res.headers.get("content-type", ""):
                        schema_json = res.json()
                        title = schema_json.get("info", {}).get("title", "API Spec")
                        version = schema_json.get("info", {}).get("version", "Unknown")
                        paths_count = len(schema_json.get("paths", {}))
                        endpoints_sample = list(schema_json.get("paths", {}).keys())[:10]

                        discovered_schemas.append({
                            "endpoint_url": target_endpoint,
                            "type": "OpenAPI / Swagger JSON",
                            "title": title,
                            "version": version,
                            "total_routes_exposed": paths_count,
                            "sample_routes": endpoints_sample,
                        })
                except Exception:
                    continue

            # 2. Probe GraphQL Introspection endpoints
            for gql_path in COMMON_GRAPHQL_PATHS:
                gql_url = f"{base_url}{gql_path}"
                try:
                    gql_res = await client.post(
                        gql_url,
                        json={"query": GRAPHQL_INTROSPECTION_QUERY},
                        headers={"Content-Type": "application/json", "User-Agent": "AETHER-APISchemaInspector/1.0"},
                    )
                    if gql_res.status_code == 200:
                        gql_data = gql_res.json()
                        if "data" in gql_data and "__schema" in gql_data.get("data", {}):
                            schema_obj = gql_data["data"]["__schema"]
                            types = schema_obj.get("types", [])
                            custom_types = [t.get("name") for t in types if t.get("name") and not t.get("name").startswith("__")][:15]

                            graphql_endpoints.append({
                                "endpoint_url": gql_url,
                                "introspection_enabled": True,
                                "query_type": schema_obj.get("queryType", {}).get("name"),
                                "mutation_type": schema_obj.get("mutationType", {}).get("name"),
                                "total_types_count": len(types),
                                "discovered_types_sample": custom_types,
                            })
                except Exception:
                    continue

        has_exposed_specs = len(discovered_schemas) > 0 or len(graphql_endpoints) > 0

        return ToolResult(
            success=True,
            data={
                "target_url": base_url,
                "api_specifications_discovered": len(discovered_schemas),
                "graphql_endpoints_discovered": len(graphql_endpoints),
                "openapi_schemas": discovered_schemas,
                "graphql_schemas": graphql_endpoints,
                "summary": (
                    f"Found {len(discovered_schemas)} OpenAPI specs and {len(graphql_endpoints)} GraphQL endpoints with open introspection."
                    if has_exposed_specs
                    else f"No publicly accessible OpenAPI documentation or open GraphQL introspection detected at standard paths on {base_url}."
                ),
            },
        )


api_schema_tool = APISchemaTool()
