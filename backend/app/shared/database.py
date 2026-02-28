from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite

from app.config import settings

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              TEXT PRIMARY KEY,
    manuscript      TEXT NOT NULL,
    genre           TEXT NOT NULL,
    tone            TEXT NOT NULL,
    output_language TEXT NOT NULL DEFAULT 'ko',
    status          TEXT NOT NULL DEFAULT 'running',
    characters_json TEXT,
    validation_json TEXT,
    output_payload  TEXT,
    error_detail    TEXT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    CONSTRAINT chk_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS pipeline_steps (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT    NOT NULL REFERENCES pipeline_runs(id),
    step      INTEGER NOT NULL,
    step_name TEXT    NOT NULL,
    status    TEXT    NOT NULL,
    detail    TEXT,
    created_at TEXT   NOT NULL,
    UNIQUE(run_id, step, status)
);

CREATE TABLE IF NOT EXISTS pipeline_cuts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT    NOT NULL REFERENCES pipeline_runs(id),
    cut_number   INTEGER NOT NULL,
    image_base64 TEXT    NOT NULL DEFAULT '',
    mime_type    TEXT    NOT NULL DEFAULT 'image/png',
    dialogue_json TEXT   NOT NULL DEFAULT '[]',
    narration    TEXT    NOT NULL DEFAULT '',
    description  TEXT    NOT NULL DEFAULT '',
    UNIQUE(run_id, cut_number)
);

CREATE INDEX IF NOT EXISTS idx_steps_run_id ON pipeline_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_cuts_run_id ON pipeline_cuts(run_id);
"""


async def init_db() -> None:
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript(_SCHEMA_SQL)
        await db.commit()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()
