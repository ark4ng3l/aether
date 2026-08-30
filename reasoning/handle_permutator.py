"""
HandlePermutationGenerator — Combinatorial & Forensic Username Permutations Engine.

Inspired by Qeeqbox Social-Analyzer & Maigret techniques.
Generates comprehensive candidate username mutations from target identity components:
- First Name, Last Name, Middle Name
- Birth Year, Birth Day, Significant Numbers
- Nicknames, Handle base, Company / Org tag
- Leetspeak mutations, punctuation separators (., _, -), and case variations
"""

from __future__ import annotations

import re
from typing import List, Dict, Set, Any, Optional


class HandlePermutationGenerator:
    """
    Generates deterministic, highly probable username permutations
    and leetspeak mutations for cross-platform OSINT enumeration.
    """

    LEET_MAP = {
        "a": ["4", "@"],
        "e": ["3"],
        "i": ["1", "!"],
        "l": ["1"],
        "o": ["0"],
        "s": ["5", "$"],
        "t": ["7"],
    }

    SEPARATORS = ["", "_", ".", "-"]

    @classmethod
    def generate(
        cls,
        first_name: str = "",
        last_name: str = "",
        middle_name: str = "",
        handle: str = "",
        nickname: str = "",
        birth_year: Optional[int | str] = None,
        company: str = "",
        limit: int = 100,
    ) -> List[str]:
        """
        Generates prioritized list of unique candidate username permutations.
        """
        candidates: Set[str] = set()

        f = cls._clean_token(first_name)
        l = cls._clean_token(last_name)
        m = cls._clean_token(middle_name)
        h = cls._clean_token(handle)
        nick = cls._clean_token(nickname)
        comp = cls._clean_token(company)

        # Years
        years = []
        if birth_year:
            y_str = str(birth_year).strip()
            if len(y_str) == 4 and y_str.isdigit():
                years.extend([y_str, y_str[2:]])  # e.g., '1995' and '95'
            elif len(y_str) == 2 and y_str.isdigit():
                years.append(y_str)

        # Base handles
        base_tokens = [t for t in [h, nick, f] if t]

        tier1_canonical: List[str] = []
        tier2_dated: List[str] = []
        tier3_leet: List[str] = []

        # 1. Direct Name Combinations (Tier 1)
        if f and l:
            f_initial = f[0]
            l_initial = l[0]

            name_pairs = [
                (f, l),
                (l, f),
                (f_initial, l),
                (f, l_initial),
                (l_initial, f),
                (l, f_initial),
            ]

            if m:
                m_initial = m[0]
                name_pairs.extend([
                    (f"{f}{m}", l),
                    (f"{f_initial}{m_initial}", l),
                    (f, f"{m_initial}{l}"),
                ])

            for part1, part2 in name_pairs:
                for sep in cls.SEPARATORS:
                    base_perm = f"{part1}{sep}{part2}"
                    tier1_canonical.append(base_perm)
                    for yr in years:
                        tier2_dated.append(f"{base_perm}{sep}{yr}")
                        tier2_dated.append(f"{base_perm}{yr}")
                        tier2_dated.append(f"{yr}{sep}{base_perm}")

        # 2. Base handles & nicknames
        for base in base_tokens:
            tier1_canonical.append(base)
            for sep in cls.SEPARATORS:
                for yr in years:
                    tier2_dated.append(f"{base}{sep}{yr}")
                    tier2_dated.append(f"{yr}{sep}{base}")
                if comp:
                    tier2_dated.append(f"{base}{sep}{comp}")
                    tier2_dated.append(f"{comp}{sep}{base}")

        # 3. Leetspeak variations
        for primary in list(tier1_canonical)[:15]:
            if len(primary) >= 4:
                tier3_leet.extend(cls._generate_leetspeak(primary)[:4])

        # Assemble in strict priority order
        all_ordered = tier1_canonical + tier2_dated + tier3_leet

        # Clean & deduplicate preserving order
        valid_handles = []
        seen = set()
        for cand in all_ordered:
            cand_clean = cand.lower().strip("._-")
            if 3 <= len(cand_clean) <= 30 and re.match(r"^[a-z0-9][a-z0-9._-]*[a-z0-9]$", cand_clean):
                if cand_clean not in seen:
                    seen.add(cand_clean)
                    valid_handles.append(cand_clean)

        return valid_handles[:limit]

    @classmethod
    def _clean_token(cls, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^a-zA-Z0-9]", "", text).lower().strip()

    @classmethod
    def _generate_leetspeak(cls, word: str) -> List[str]:
        variants = {word}
        for char, replacements in cls.LEET_MAP.items():
            new_vars = set()
            for v in variants:
                if char in v:
                    for rep in replacements:
                        new_vars.add(v.replace(char, rep, 1))
            variants.update(new_vars)
        variants.discard(word)
        return list(variants)


handle_permutator = HandlePermutationGenerator()
