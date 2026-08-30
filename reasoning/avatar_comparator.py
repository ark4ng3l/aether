"""
AvatarPerceptualComparator — Perceptual Image Hashing & Cross-Profile Avatar Matcher.

Inspired by Maigret & Social-Analyzer visual identity heuristics.
Computes dHash (difference hash) and aHash (average hash) to correlate profile avatars
across different platforms without external API dependencies.
"""

from __future__ import annotations

import io
import hashlib
from typing import Dict, Any, List, Optional, Tuple
import httpx
from PIL import Image

from aether.core.logger import logger


class AvatarPerceptualComparator:
    """
    Forensic image hashing engine to match avatars across platforms.
    """

    @classmethod
    def compute_dhash(cls, image_bytes: bytes, hash_size: int = 8) -> str:
        """
        Computes 64-bit difference hash (dHash) from image bytes.
        Fast, robust to resizing, compression artifacts, and minor color shifts.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to grayscale and resize to (hash_size + 1, hash_size)
                img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())

                # Compare adjacent pixels
                diff = []
                for row in range(hash_size):
                    for col in range(hash_size):
                        pixel_left = pixels[row * (hash_size + 1) + col]
                        pixel_right = pixels[row * (hash_size + 1) + col + 1]
                        diff.append(pixel_left > pixel_right)

                # Convert boolean array to hex string
                decimal_value = 0
                for index, value in enumerate(diff):
                    if value:
                        decimal_value += 1 << index
                return f"{decimal_value:016x}"
        except Exception as exc:
            logger.debug(f"dHash computation failed: {exc}")
            # Fallback to standard MD5 on raw bytes
            return hashlib.md5(image_bytes).hexdigest()[:16]

    @classmethod
    def compute_ahash(cls, image_bytes: bytes, hash_size: int = 8) -> str:
        """
        Computes Average Hash (aHash) for baseline structural comparison.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = "".join(["1" if p > avg else "0" for p in pixels])
                return f"{int(bits, 2):016x}"
        except Exception:
            return ""

    @classmethod
    def hamming_distance(cls, hash1: str, hash2: str) -> int:
        """
        Calculates Hamming distance (differing bits) between two 16-character hex hashes.
        Distance 0 = identical image. Distance <= 6 = highly probable match.
        """
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64

        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            xor_val = val1 ^ val2
            return bin(xor_val).count("1")
        except ValueError:
            return 64

    @classmethod
    def compare_hashes(cls, hash_a: str, hash_b: str) -> Dict[str, Any]:
        """
        Compares two hashes and calculates similarity percentage and match classification.
        """
        dist = cls.hamming_distance(hash_a, hash_b)
        similarity_pct = max(0.0, min(100.0, (1.0 - (dist / 64.0)) * 100.0))

        if dist == 0:
            verdict = "EXACT_MATCH"
            is_match = True
        elif dist <= 4:
            verdict = "HIGH_CONFIDENCE_MATCH"
            is_match = True
        elif dist <= 8:
            verdict = "PROBABLE_MUTATION"
            is_match = True
        elif dist <= 14:
            verdict = "POSSIBLE_SIMILARITY"
            is_match = False
        else:
            verdict = "DISTINCT_AVATAR"
            is_match = False

        return {
            "hash_a": hash_a,
            "hash_b": hash_b,
            "hamming_distance": dist,
            "similarity_pct": round(similarity_pct, 2),
            "is_match": is_match,
            "verdict": verdict,
        }

    @classmethod
    async def fetch_and_hash_avatar(cls, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches an avatar image from URL and computes perceptual fingerprints.
        """
        if not url or not url.startswith("http"):
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, proxy=proxy) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200 and len(resp.content) > 100:
                    dhash = cls.compute_dhash(resp.content)
                    ahash = cls.compute_ahash(resp.content)
                    return {
                        "url": url,
                        "content_type": resp.headers.get("content-type", "image/jpeg"),
                        "size_bytes": len(resp.content),
                        "dhash": dhash,
                        "ahash": ahash,
                    }
        except Exception as exc:
            logger.debug(f"Failed to fetch avatar from {url}: {exc}")

        return None


avatar_comparator = AvatarPerceptualComparator()
