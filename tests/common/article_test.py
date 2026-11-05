"""
### Unit tests for src/common/article.py
Tests the Article Pydantic model construction, optional fields, and serialization.
"""

from common.article import Article


class TestArticle:
    ### Construction

    def test_all_fields(self):
        article = Article(
            source="BBC",
            title="Test Headline",
            summary="A short summary.",
            link="https://example.com/news/1",
            published_at="2026-03-28T10:00:00+00:00",
            fetched_at="2026-03-28T10:05:00+00:00",
        )
        assert article.source == "BBC"
        assert article.title == "Test Headline"
        assert article.summary == "A short summary."
        assert article.link == "https://example.com/news/1"
        assert article.published_at == "2026-03-28T10:00:00+00:00"
        assert article.fetched_at == "2026-03-28T10:05:00+00:00"

    def test_all_fields_none(self):
        article = Article(
            source=None,
            title=None,
            summary=None,
            link=None,
            published_at=None,
            fetched_at=None,
        )
        assert article.source is None
        assert article.title is None

    def test_partial_fields(self):
        # Pydantic v2 Optional[str] fields are required — must pass None explicitly
        article = Article(
            source="Reuters",
            title="Breaking News",
            summary=None,
            link=None,
            published_at=None,
            fetched_at=None,
        )
        assert article.source == "Reuters"
        assert article.title == "Breaking News"
        assert article.summary is None
        assert article.link is None

    ### Serialisation

    def test_model_dump_returns_dict(self):
        article = Article(
            source="TechCrunch",
            title="AI News",
            summary="Details here.",
            link=None,
            published_at=None,
            fetched_at=None,
        )
        result = article.model_dump()
        assert isinstance(result, dict)
        assert result["source"] == "TechCrunch"
        assert result["title"] == "AI News"
        assert result["summary"] == "Details here."

    def test_model_dump_includes_none_values(self):
        article = Article(
            source="Wired",
            title=None,
            summary=None,
            link=None,
            published_at=None,
            fetched_at=None,
        )
        result = article.model_dump()
        assert "link" in result
        assert result["link"] is None

    def test_model_dump_all_keys_present(self):
        article = Article(
            source=None,
            title=None,
            summary=None,
            link=None,
            published_at=None,
            fetched_at=None,
        )
        result = article.model_dump()
        expected_keys = {
            "source",
            "title",
            "summary",
            "link",
            "published_at",
            "fetched_at",
        }
        assert expected_keys == set(result.keys())
