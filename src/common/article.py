from pydantic import BaseModel


class Article(BaseModel):
    source: str | None
    title: str | None
    summary: str | None
    link: str | None
    published_at: str | None
    fetched_at: str | None
