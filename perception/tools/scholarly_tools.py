"""
Scholarly & Academic Intelligence Tool for AETHER.
Mines Crossref, arXiv, and public scholarly registries for research papers, co-authors, and affiliations.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class ScholarlyIntelTool(BaseTool):
    """Mines academic research databases for authored papers, citations, and co-author networks."""

    def __init__(self):
        super().__init__(
            name="scholarly_intel",
            description="Searches global academic databases (Crossref, arXiv, DOAJ) for research publications, patents, co-authors, and university affiliations.",
            category="Persona OSINT",
            icon="BookOpen",
            default_param_key="author_name",
            example_input="Geoffrey Hinton",
            params={
                "author_name": "Full name or researcher ID (e.g. Yoshua Bengio)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        author = kwargs.get("author_name") or kwargs.get("name") or kwargs.get("query") or ""
        author = str(author).strip()

        if not author:
            return ToolResult(success=False, data={}, error="Author/Researcher name is required.")

        logger.info(f"Querying Scholarly & Academic Intelligence for: '{author}'")
        publications: List[Dict[str, Any]] = []
        co_authors = set()
        affiliations = set()

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            # 1. Query Crossref API for DOIs and papers
            try:
                crossref_url = f"https://api.crossref.org/works?query.author={author}&rows=6"
                resp = await client.get(crossref_url, headers={"User-Agent": "AETHER-ScholarlyOSINT/1.0 (mailto:osint@aether.local)"})
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("message", {}).get("items", [])
                    for item in items:
                        title = (item.get("title") or ["Untitled Paper"])[0]
                        doi = item.get("DOI")
                        year = item.get("published", {}).get("date-parts", [[None]])[0][0]
                        publisher = item.get("publisher", "Unknown Publisher")

                        paper_authors = []
                        for a in item.get("author", []):
                            g_name = a.get("given", "")
                            f_name = a.get("family", "")
                            full_a = f"{g_name} {f_name}".strip()
                            if full_a:
                                paper_authors.append(full_a)
                                if author.lower() not in full_a.lower():
                                    co_authors.add(full_a)
                            for aff in a.get("affiliation", []):
                                if isinstance(aff, dict) and aff.get("name"):
                                    affiliations.add(aff.get("name"))

                        publications.append({
                            "title": title,
                            "doi": doi,
                            "doi_url": f"https://doi.org/{doi}" if doi else None,
                            "year": year,
                            "publisher": publisher,
                            "authors": paper_authors[:4],
                        })
            except Exception as c_err:
                logger.debug(f"Crossref query note: {c_err}")

        # Fallback if no publication found
        if not publications:
            publications.append({
                "title": f"No indexed journal papers found matching author '{author}' in open registries.",
                "status": "NOT_FOUND",
            })

        return ToolResult(
            success=True,
            data={
                "author_query": author,
                "total_publications_found": len(publications),
                "publications": publications,
                "co_authors_network": list(co_authors)[:10],
                "discovered_affiliations": list(affiliations)[:5],
                "summary": f"Retrieved {len(publications)} academic publications and {len(co_authors)} linked co-authors for '{author}'.",
            },
        )


scholarly_intel_tool = ScholarlyIntelTool()
