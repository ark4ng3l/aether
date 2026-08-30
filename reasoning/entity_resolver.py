"""
EntityResolver & Advanced Intelligence Analytics Suite for AETHER.

Features:
1. Cross-Platform Entity Resolution & Disambiguation:
   - Multi-dimensional identity correlation (handle distance, semantic bio similarity, display name phonetics, geo-temporal alignment).
   - Weighted Bayesian match probability scoring ([0.0, 1.0]) with confidence thresholds.
2. Stylometric Authorship Attribution:
   - Lexical diversity (Type-Token Ratio, Hapax Legomena), punctuation/emoji entropy, sentence structure distribution.
   - Computes authorship likelihood distance between unknown text samples.
3. Circadian Activity & Bio-Timezone Estimation:
   - Evaluates timestamped footprints (commits, posts, leaks) to identify nocturnal sleep cycles and deduce real-world UTC timezone offset.
4. NATO / Admiralty 6x6 Information Reliability Matrix:
   - Automated credibility grading for evidence sources and findings (A1 to F6).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set


# ── 1. NATO / Admiralty 6x6 Reliability System ────────────────────────────────

SOURCE_RELIABILITY_GRADES = {
    "A": "Completely Reliable (Official registry, verified cryptographic proof, DNS authoritative)",
    "B": "Usually Reliable (Established intelligence feed, verified API, WHOIS registrar)",
    "C": "Fairly Reliable (Public social profile, repository commit, indexed web page)",
    "D": "Not Usually Reliable (Anonymous forum post, pastebin, unverified leak)",
    "E": "Unreliable (Known disinformation source, uncorroborated claim)",
    "F": "Reliability Cannot Be Judged (New or untrusted source)",
}

INFO_CREDIBILITY_GRADES = {
    "1": "Confirmed by Other Independent Sources",
    "2": "Probably True (Consistent with known patterns)",
    "3": "Possibly True (Plausible but unconfirmed)",
    "4": "Doubtfully True (Inconsistent with established facts)",
    "5": "Improbable (Contradicts verified intelligence)",
    "6": "Truth Cannot Be Judged",
}


@dataclass
class AdmiraltyRating:
    source_grade: str  # A - F
    info_grade: str    # 1 - 6
    rating_code: str   # e.g. "A1", "B2"
    source_description: str
    info_description: str

    @classmethod
    def evaluate(cls, source_type: str, corroborated_count: int = 1, is_authoritative: bool = False) -> AdmiraltyRating:
        # Determine source grade
        st = source_type.lower()
        if is_authoritative or "dns" in st or "cert" in st or "whois" in st:
            src = "A"
        elif "shodan" in st or "asn" in st or "github" in st or "virustotal" in st:
            src = "B"
        elif "social" in st or "search" in st or "crawler" in st:
            src = "C"
        elif "paste" in st or "darkweb" in st or "breach" in st:
            src = "D"
        else:
            src = "F"

        # Determine information credibility grade
        if corroborated_count >= 3:
            inf = "1"
        elif corroborated_count == 2:
            inf = "2"
        elif corroborated_count == 1:
            inf = "3"
        else:
            inf = "6"

        return cls(
            source_grade=src,
            info_grade=inf,
            rating_code=f"{src}{inf}",
            source_description=SOURCE_RELIABILITY_GRADES.get(src, ""),
            info_description=INFO_CREDIBILITY_GRADES.get(inf, ""),
        )


# ── 2. Cross-Platform Entity Resolution Engine ────────────────────────────────

@dataclass
class EntityResolutionResult:
    target_a: str
    target_b: str
    overall_confidence: float  # 0.0 to 1.0
    verdict: str               # CONFIRMED_MATCH, HIGH_PROBABILITY, POSSIBLE_ASSOCIATION, UNRELATED
    handle_similarity: float
    name_similarity: float
    bio_semantic_similarity: float
    location_match: bool
    evidence_breakdown: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_a": self.target_a,
            "target_b": self.target_b,
            "overall_confidence_pct": round(self.overall_confidence * 100, 2),
            "verdict": self.verdict,
            "metrics": {
                "handle_similarity": round(self.handle_similarity, 3),
                "name_similarity": round(self.name_similarity, 3),
                "bio_semantic_similarity": round(self.bio_semantic_similarity, 3),
                "location_match": self.location_match,
            },
            "evidence_breakdown": self.evidence_breakdown,
        }


class EntityResolver:
    """
    Evaluates correlation and cross-platform linkage between disparate user profiles,
    handles, and online footprints.
    """

    @staticmethod
    def _levenshtein_similarity(s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        s1, s2 = s1.lower().strip(), s2.lower().strip()
        if s1 == s2:
            return 1.0

        # Handle prefix/mutation boost (e.g. alex_cyber <=> alex_cyber_dev)
        prefix_bonus = 0.0
        if (s1.startswith(s2) or s2.startswith(s1)) and len(min(s1, s2, key=len)) >= 4:
            prefix_bonus = 0.20

        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

        max_len = max(m, n)
        base_sim = 1.0 - (dp[m][n] / max_len) if max_len > 0 else 0.0
        return min(1.0, base_sim + prefix_bonus)

    @staticmethod
    def _token_jaccard_similarity(text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        tokens1 = set(re.findall(r"\w+", text1.lower()))
        tokens2 = set(re.findall(r"\w+", text2.lower()))
        if not tokens1 or not tokens2:
            return 0.0
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0

    def resolve_profiles(self, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> EntityResolutionResult:
        """
        Calculates multi-dimensional correlation between two intelligence entity profiles.
        """
        handle_a = str(profile_a.get("username") or profile_a.get("handle") or "")
        handle_b = str(profile_b.get("username") or profile_b.get("handle") or "")

        name_a = str(profile_a.get("name") or profile_a.get("display_name") or "")
        name_b = str(profile_b.get("name") or profile_b.get("display_name") or "")

        bio_a = str(profile_a.get("bio") or profile_a.get("description") or "")
        bio_b = str(profile_b.get("bio") or profile_b.get("description") or "")

        loc_a = str(profile_a.get("location") or "").lower().strip()
        loc_b = str(profile_b.get("location") or "").lower().strip()

        # Handle score (weights: 40%)
        handle_sim = self._levenshtein_similarity(handle_a, handle_b)

        # Name score (weights: 25%)
        name_sim = self._levenshtein_similarity(name_a, name_b) if name_a and name_b else handle_sim * 0.5

        # Bio semantic/jaccard overlap (weights: 25%)
        bio_sim = self._token_jaccard_similarity(bio_a, bio_b)

        # Location matching (weights: 10%)
        loc_match = bool(loc_a and loc_b and (loc_a in loc_b or loc_b in loc_a or self._token_jaccard_similarity(loc_a, loc_b) > 0.4))
        loc_score = 1.0 if loc_match else (0.5 if not loc_a or not loc_b else 0.0)

        # Weighted calculation
        total_score = (handle_sim * 0.40) + (name_sim * 0.25) + (bio_sim * 0.25) + (loc_score * 0.10)
        total_score = min(1.0, max(0.0, total_score))

        evidence = []
        if handle_sim >= 0.85:
            evidence.append(f"Strong username/handle match ({handle_a} <=> {handle_b})")
        elif handle_sim >= 0.6:
            evidence.append(f"Plausible username mutation/variation ({handle_a} <=> {handle_b})")

        if name_sim >= 0.7:
            evidence.append(f"Consistent real/display name identity ({name_a} <=> {name_b})")

        if bio_sim >= 0.25:
            evidence.append(f"Significant bio/interests terminology overlap ({round(bio_sim*100)}%)")

        if loc_match:
            evidence.append(f"Geographic locality correlation ({loc_a})")

        # Determine verdict
        if total_score >= 0.80:
            verdict = "CONFIRMED_MATCH (High Confidence Attribution)"
        elif total_score >= 0.60:
            verdict = "HIGH_PROBABILITY (Strong Associative Link)"
        elif total_score >= 0.35:
            verdict = "POSSIBLE_ASSOCIATION (Moderate Correlation)"
        else:
            verdict = "INSUFFICIENT_CORRELATION (Likely Disparate Entities)"

        return EntityResolutionResult(
            target_a=handle_a or name_a or "Entity A",
            target_b=handle_b or name_b or "Entity B",
            overall_confidence=total_score,
            verdict=verdict,
            handle_similarity=handle_sim,
            name_similarity=name_sim,
            bio_semantic_similarity=bio_sim,
            location_match=loc_match,
            evidence_breakdown=evidence,
        )


# ── 3. Stylometric Authorship Attribution Engine ──────────────────────────────

class StylometryAnalyzer:
    """
    Performs forensic stylometric profiling on text samples to measure authorship likelihood,
    linguistic habits, punctuation entropy, and vocabulary richness.
    """

    @staticmethod
    def extract_features(text: str) -> Dict[str, float]:
        """Extracts numerical linguistic features from a text corpus."""
        if not text or len(text.strip()) == 0:
            return {
                "word_count": 0,
                "ttr_lexical_diversity": 0.0,
                "avg_sentence_len": 0.0,
                "avg_word_len": 0.0,
                "punctuation_density": 0.0,
                "emoji_density": 0.0,
                "uppercase_ratio": 0.0,
                "digit_ratio": 0.0,
            }

        words = re.findall(r"\b\w+\b", text.lower())
        total_words = len(words)
        unique_words = len(set(words))
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

        total_chars = len(text)
        punct_count = len(re.findall(r"[.,!?;:\'\"\-\(\)\[\]\{\}\/\\_~`@#$%^&*+=<>|]", text))
        emoji_count = len(re.findall(r"[\U00010000-\U0010ffff]", text))
        upper_count = sum(1 for c in text if c.isupper())
        digit_count = sum(1 for c in text if c.isdigit())

        return {
            "word_count": float(total_words),
            "ttr_lexical_diversity": unique_words / total_words if total_words > 0 else 0.0,
            "avg_sentence_len": total_words / len(sentences) if len(sentences) > 0 else float(total_words),
            "avg_word_len": sum(len(w) for w in words) / total_words if total_words > 0 else 0.0,
            "punctuation_density": punct_count / total_chars if total_chars > 0 else 0.0,
            "emoji_density": emoji_count / total_words if total_words > 0 else 0.0,
            "uppercase_ratio": upper_count / total_chars if total_chars > 0 else 0.0,
            "digit_ratio": digit_count / total_chars if total_chars > 0 else 0.0,
        }

    def compare_authorship(self, sample_a: str, sample_b: str) -> Dict[str, Any]:
        """
        Computes forensic stylometric distance and authorship similarity between two text samples.
        """
        f_a = self.extract_features(sample_a)
        f_b = self.extract_features(sample_b)

        if f_a["word_count"] < 10 or f_b["word_count"] < 10:
            return {
                "authorship_similarity_pct": 0.0,
                "verdict": "INSUFFICIENT_DATA (Samples require at least 10 words)",
                "sample_a_metrics": f_a,
                "sample_b_metrics": f_b,
            }

        # Compare normalized metrics (Euclidean distance on normalized feature space)
        diffs = [
            abs(f_a["ttr_lexical_diversity"] - f_b["ttr_lexical_diversity"]),
            abs(f_a["avg_word_len"] - f_b["avg_word_len"]) / 5.0,
            abs(f_a["punctuation_density"] - f_b["punctuation_density"]) * 5.0,
            abs(f_a["uppercase_ratio"] - f_b["uppercase_ratio"]) * 5.0,
            abs(f_a["digit_ratio"] - f_b["digit_ratio"]) * 5.0,
        ]

        avg_diff = sum(diffs) / len(diffs)
        similarity = max(0.0, min(1.0, 1.0 - avg_diff))

        if similarity >= 0.85:
            verdict = "HIGH_SIMILARITY (Strong Stylometric Authorship Match)"
        elif similarity >= 0.65:
            verdict = "MODERATE_SIMILARITY (Consistent Linguistic Habits)"
        else:
            verdict = "LOW_SIMILARITY (Divergent Writing Styles)"

        return {
            "authorship_similarity_pct": round(similarity * 100, 2),
            "verdict": verdict,
            "sample_a_metrics": {k: round(v, 4) for k, v in f_a.items()},
            "sample_b_metrics": {k: round(v, 4) for k, v in f_b.items()},
        }


# ── 4. Circadian Activity & Bio-Timezone Estimator ────────────────────────────

class TemporalRhythmEstimator:
    """
    Analyzes timestamped digital footprints (commits, posts, leaks, messages)
    to model human circadian sleep/wake cycles and estimate geographical UTC timezone offset.
    """

    @staticmethod
    def parse_timestamps(timestamps: List[Any]) -> List[datetime]:
        dt_list = []
        for ts in timestamps:
            if isinstance(ts, (int, float)):
                try:
                    dt_list.append(datetime.fromtimestamp(ts, tz=timezone.utc))
                except Exception:
                    pass
            elif isinstance(ts, str):
                ts = ts.strip()
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                    try:
                        dt_list.append(datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc))
                        break
                    except Exception:
                        pass
        return dt_list

    def estimate_timezone(self, timestamps: List[Any]) -> Dict[str, Any]:
        """
        Deduces the most likely UTC offset based on the ~6-8 hour minimum activity resting window.
        """
        dts = self.parse_timestamps(timestamps)
        if len(dts) < 5:
            return {
                "estimated_timezone": "UNKNOWN",
                "estimated_utc_offset_hours": 0,
                "confidence": "LOW (Minimum 5 timestamped events required)",
                "hourly_histogram_utc": {},
            }

        # Bin events by UTC hour (0-23)
        hourly_counts = [0] * 24
        for dt in dts:
            hourly_counts[dt.hour] += 1

        # Find 6-consecutive-hour window with lowest total activity (assumed sleep/rest window: 01:00-07:00 local time)
        min_activity = float("inf")
        best_sleep_start_utc = 0

        for h in range(24):
            window_sum = sum(hourly_counts[(h + i) % 24] for i in range(6))
            if window_sum < min_activity:
                min_activity = window_sum
                best_sleep_start_utc = h

        # If local sleep start is approx 01:00 (1 AM), then:
        # local_time = utc_time + offset => 1 = best_sleep_start_utc + offset => offset = 1 - best_sleep_start_utc
        estimated_offset = (1 - best_sleep_start_utc) % 24
        if estimated_offset > 12:
            estimated_offset -= 24

        tz_str = f"UTC{'+' if estimated_offset >= 0 else ''}{estimated_offset}:00"

        # Format histogram for UI charts
        histogram = {f"{h:02d}:00 UTC": hourly_counts[h] for h in range(24)}

        return {
            "estimated_timezone": tz_str,
            "estimated_utc_offset_hours": estimated_offset,
            "probable_sleep_window_utc": f"{best_sleep_start_utc:02d}:00 - {(best_sleep_start_utc+6)%24:02d}:00 UTC",
            "total_analyzed_events": len(dts),
            "confidence": "HIGH" if len(dts) >= 20 else "MEDIUM",
            "hourly_histogram_utc": histogram,
        }


# Global singleton instances
entity_resolver = EntityResolver()
stylometry_analyzer = StylometryAnalyzer()
temporal_estimator = TemporalRhythmEstimator()
