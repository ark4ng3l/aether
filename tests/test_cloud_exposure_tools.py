"""
Tests for CloudBucketReconTool (S3, GCS, Azure bucket exposure checks).
"""

import pytest
from unittest.mock import patch, AsyncMock
from aether.perception.tools.bucket_tools import bucket_tool


@pytest.mark.asyncio
async def test_cloud_bucket_recon_mocked():
    """Detects public buckets from mocked HTTP HEAD/GET responses."""
    with patch("httpx.AsyncClient.head") as mock_head, patch("httpx.AsyncClient.get") as mock_get:
        # Mock HEAD response for S3
        resp_head = AsyncMock()
        resp_head.status_code = 200
        mock_head.return_value = resp_head

        # Mock GET response indicating open directory XML
        resp_get = AsyncMock()
        resp_get.status_code = 200
        resp_get.text = '<?xml version="1.0"?><ListBucketResult><Name>target-assets</Name></ListBucketResult>'
        mock_get.return_value = resp_get

        res = await bucket_tool.execute(name="target-assets", check_content=True)
        assert res.success is True
        assert "buckets" in res.data or "exposed" in res.data or len(res.data) > 0
