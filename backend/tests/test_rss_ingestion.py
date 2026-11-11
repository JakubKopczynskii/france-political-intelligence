import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.rss_ingestion import (
    compute_fingerprint,
    apply_topic_tags,
    detect_duplicates_in_batch,
    normalize_entry,
)


# --- compute_fingerprint ---

def test_fingerprint_consistent():
    fp1 = compute_fingerprint("https://example.com/article/1", "Some headline")
    fp2 = compute_fingerprint("https://example.com/article/1", "Some headline")
    assert fp1 == fp2


def test_fingerprint_is_sha256_hex():
    fp = compute_fingerprint("https://example.com", "title")
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_different_for_different_inputs():
    fp1 = compute_fingerprint("https://example.com/1", "title")
    fp2 = compute_fingerprint("https://example.com/2", "title")
    assert fp1 != fp2


def test_fingerprint_case_insensitive():
    fp1 = compute_fingerprint("HTTPS://EXAMPLE.COM/1", "TITLE")
    fp2 = compute_fingerprint("https://example.com/1", "title")
    assert fp1 == fp2


# --- apply_topic_tags ---

def test_fiscal_tag():
    tags = apply_topic_tags("Budget de la France", "")
    assert "fiscal" in tags


def test_ecb_tag():
    tags = apply_topic_tags("BCE taux directeur inflation", "")
    assert "ecb" in tags


def test_politics_tag():
    tags = apply_topic_tags("Élection présidentielle en France", "")
    assert "politics" in tags


def test_energy_tag():
    tags = apply_topic_tags("Nucléaire et énergie renouvelable", "")
    assert "energy" in tags


def test_defence_tag():
    tags = apply_topic_tags("NATO defence spending increases", "")
    assert "defence" in tags


def test_multiple_tags():
    tags = apply_topic_tags("Budget déficit et BCE taux", "")
    assert "fiscal" in tags
    assert "ecb" in tags


def test_empty_input():
    tags = apply_topic_tags("", "")
    assert isinstance(tags, list)
    assert len(tags) == 0


def test_irrelevant_text():
    tags = apply_topic_tags("Recipe for chocolate cake", "bake at 180 degrees")
    assert len(tags) == 0


def test_macro_tag():
    tags = apply_topic_tags("French GDP growth slows amid recession fears", "")
    assert "macro" in tags


def test_companies_tag():
    tags = apply_topic_tags("TotalEnergies profit results beat estimates", "")
    assert "companies" in tags


# --- detect_duplicates_in_batch ---

def _make_article(url, title):
    return {
        "url": url,
        "title": title,
        "fingerprint": compute_fingerprint(url, title),
    }


def test_no_duplicates_in_batch():
    articles = [
        _make_article("https://a.com/1", "Title 1"),
        _make_article("https://a.com/2", "Title 2"),
        _make_article("https://a.com/3", "Title 3"),
    ]
    result = detect_duplicates_in_batch(articles)
    assert all(not a["is_duplicate"] for a in result)


def test_duplicates_detected():
    a1 = _make_article("https://a.com/1", "Same title")
    a2 = _make_article("https://a.com/1", "Same title")
    a3 = _make_article("https://a.com/2", "Different title")
    result = detect_duplicates_in_batch([a1, a2, a3])
    assert result[0]["is_duplicate"] is False
    assert result[1]["is_duplicate"] is True
    assert result[2]["is_duplicate"] is False


def test_empty_batch():
    result = detect_duplicates_in_batch([])
    assert result == []


def test_single_article_not_duplicate():
    articles = [_make_article("https://a.com/1", "Title")]
    result = detect_duplicates_in_batch(articles)
    assert result[0]["is_duplicate"] is False


# --- normalize_entry ---

def test_normalize_entry_basic():
    entry = {
        "title": "Test Article",
        "link": "https://example.com/test",
        "summary": "This is a test article about fiscal policy.",
    }
    result = normalize_entry(entry, "Test Source")
    assert result["title"] == "Test Article"
    assert result["url"] == "https://example.com/test"
    assert "fiscal" in __import__("json").loads(result["topic_tags"])


def test_normalize_entry_missing_fields():
    entry = {"title": "Minimal", "link": "https://example.com/min"}
    result = normalize_entry(entry, "Test")
    assert result["content_snippet"] == ""
    assert result["published_at"] is None


# --- Async feed fetch (error handling) ---

@pytest.mark.asyncio
async def test_fetch_feed_handles_bad_url():
    from services.rss_ingestion import fetch_feed
    result = await fetch_feed("https://this-url-definitely-does-not-exist-xyz123.com/feed.xml", timeout=5)
    assert result["success"] is False
    assert result["error"] is not None
    assert result["entries"] == []
