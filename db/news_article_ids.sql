-- news_article_ids: the scheduler's persistent dedup store (database: postgres).
--
-- One row per article delivered to Kafka. article_id_hash is the MD5 of
-- link + published_at + source; created_at is the date, in the DB session/server
-- TimeZone, when the article was marked seen after Kafka confirmed delivery (the
-- scheduler sends a UTC timestamp, which Postgres casts to a date in that TimeZone).
-- The scheduler warms its in-memory cache with the rows from today and the previous
-- DEDUP_WINDOW_DAYS full days (created_at >= CURRENT_DATE - n), reloads it daily at
-- DEDUP_REFRESH_AT, and inserts with ON CONFLICT DO NOTHING.
--
-- Idempotent: safe to run against a database where the table already exists.
-- Run it from the repo root (vault CLI on the host, VAULT_ADDR/VAULT_TOKEN exported):
--   docker exec -i postgres psql -v ON_ERROR_STOP=1 -d postgres \
--     -U "$(vault kv get -field=POSTGRES_USER secret/CREDENTIALS)" < db/news_article_ids.sql

CREATE TABLE IF NOT EXISTS news_article_ids (
    article_id_hash varchar NOT NULL,
    created_at      date    NOT NULL,
    CONSTRAINT news_article_ids_pk PRIMARY KEY (article_id_hash)
);
