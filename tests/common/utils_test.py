"""
### Unit tests for src/common/utils.py
Tests generate_id and parse_to_iso utility functions.
"""
import hashlib
import pytest
from unittest.mock import patch
from datetime import timezone

from common.utils import generate_id, parse_to_iso


class TestGenerateId:

    ### MD5 hashing

    def test_known_hash(self):
        expected = hashlib.md5("hello".encode()).hexdigest()
        assert generate_id("hello") == expected

    def test_different_inputs_produce_different_hashes(self):
        assert generate_id("abc") != generate_id("def")

    def test_same_input_always_same_hash(self):
        assert generate_id("stable_key") == generate_id("stable_key")

    def test_returns_32_char_hex_string(self):
        result = generate_id("any_key")
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_string(self):
        expected = hashlib.md5(b"").hexdigest()
        assert generate_id("") == expected


class TestParseToIso:

    ### Valid RFC 2822 dates

    def test_parses_rfc2822_with_offset(self):
        result = parse_to_iso("Tue, 17 Mar 2026 21:39:17 +0000")
        assert result == "2026-03-17T21:39:17+00:00"

    def test_parses_rfc2822_with_gmt(self):
        result = parse_to_iso("Wed, 18 Mar 2026 00:04:34 GMT")
        assert "2026-03-18" in result

    def test_returns_iso_format_string(self):
        result = parse_to_iso("Mon, 01 Jan 2026 12:00:00 +0000")
        # ISO 8601 format check
        assert "T" in result
        assert "2026-01-01" in result

    ### Fallback behaviour

    def test_invalid_date_returns_current_utc(self):
        with patch("common.utils.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2026-03-28T00:00:00+00:00"
            result = parse_to_iso("not-a-date")
        assert result == "2026-03-28T00:00:00+00:00"

    def test_empty_string_falls_back(self):
        # Should not raise — must return a string
        result = parse_to_iso("")
        assert isinstance(result, str)
        assert len(result) > 0