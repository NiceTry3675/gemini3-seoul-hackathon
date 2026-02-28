from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.domain.conti.schemas import ContiRequest, ContiResult, PipelineProgress

logger = logging.getLogger(__name__)


class PipelineRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def create_run(self, request: ContiRequest) -> str:
        run_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO pipeline_runs (id, manuscript, genre, tone, output_language, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (run_id, request.manuscript, request.genre, request.tone, request.output_language, now),
        )
        await self._db.commit()
        return run_id

    async def save_step(self, run_id: str, progress: PipelineProgress) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT OR REPLACE INTO pipeline_steps (run_id, step, step_name, status, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, progress.step, progress.step_name, progress.status, progress.detail, now),
        )
        await self._db.commit()

    async def save_result(self, run_id: str, result: ContiResult) -> None:
        now = datetime.now(timezone.utc).isoformat()
        chars_json = result.characters.model_dump_json() if result.characters else None
        val_json = result.validation_report.model_dump_json() if result.validation_report else None
        output_payload = result.model_dump_json()

        await self._db.execute(
            "UPDATE pipeline_runs SET status='completed', characters_json=?, validation_json=?, "
            "output_payload=?, finished_at=? WHERE id=?",
            (chars_json, val_json, output_payload, now, run_id),
        )
        for cut in result.cuts:
            await self._db.execute(
                "INSERT INTO pipeline_cuts (run_id, cut_number, image_base64, mime_type, dialogue_json, narration, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    cut.cut_number,
                    cut.image_base64,
                    cut.mime_type,
                    json.dumps(cut.dialogue, ensure_ascii=False),
                    cut.narration,
                    cut.description,
                ),
            )
        await self._db.commit()

    async def mark_failed(self, run_id: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE pipeline_runs SET status='failed', error_detail=?, finished_at=? WHERE id=?",
            (error, now, run_id),
        )
        await self._db.commit()

    async def list_runs(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT r.id, r.manuscript, r.genre, r.tone, r.status, r.started_at, r.finished_at, "
            "(SELECT COUNT(*) FROM pipeline_cuts c WHERE c.run_id = r.id) AS cut_count "
            "FROM pipeline_runs r ORDER BY r.started_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "manuscript_preview": row["manuscript"][:200],
                "genre": row["genre"],
                "tone": row["tone"],
                "status": row["status"],
                "cut_count": row["cut_count"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
            }
            for row in rows
        ]

    async def get_run(self, run_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        result: dict = {
            "id": row["id"],
            "manuscript": row["manuscript"],
            "genre": row["genre"],
            "tone": row["tone"],
            "output_language": row["output_language"],
            "status": row["status"],
            "characters": json.loads(row["characters_json"]) if row["characters_json"] else None,
            "validation_report": json.loads(row["validation_json"]) if row["validation_json"] else None,
            "error_detail": row["error_detail"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
        }

        # Load cuts
        cursor = await self._db.execute(
            "SELECT * FROM pipeline_cuts WHERE run_id = ? ORDER BY cut_number", (run_id,)
        )
        cut_rows = await cursor.fetchall()
        result["cuts"] = [
            {
                "cut_number": c["cut_number"],
                "image_base64": c["image_base64"],
                "mime_type": c["mime_type"],
                "dialogue": json.loads(c["dialogue_json"]),
                "narration": c["narration"],
                "description": c["description"],
            }
            for c in cut_rows
        ]

        # Load steps
        cursor = await self._db.execute(
            "SELECT step, step_name, status, detail FROM pipeline_steps WHERE run_id = ? ORDER BY step, id",
            (run_id,),
        )
        step_rows = await cursor.fetchall()
        result["steps"] = [
            {
                "step": s["step"],
                "step_name": s["step_name"],
                "status": s["status"],
                "detail": s["detail"],
            }
            for s in step_rows
        ]

        return result
