"""SQLite-backed persistence for narratives and signals."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from models.schemas import AssetClass, Narrative, RiskLevel, Signal, SignalSource

DB_PATH = Path(__file__).parent.parent / "sentinel.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS narratives (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            affected_assets TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            trend TEXT NOT NULL DEFAULT 'stable',
            confidence REAL NOT NULL DEFAULT 0.5,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            url TEXT,
            timestamp TEXT NOT NULL,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS narrative_signals (
            narrative_id TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            PRIMARY KEY (narrative_id, signal_id),
            FOREIGN KEY (narrative_id) REFERENCES narratives(id),
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );

        CREATE TABLE IF NOT EXISTS narrative_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            narrative_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            trend TEXT NOT NULL,
            summary TEXT NOT NULL,
            FOREIGN KEY (narrative_id) REFERENCES narratives(id)
        );
    """
    )
    conn.commit()
    conn.close()


def save_narrative(narrative: Narrative) -> None:
    """Save or update a narrative and its associated signals."""
    conn = _get_conn()

    conn.execute(
        """INSERT OR REPLACE INTO narratives
        (id, title, summary, risk_level, affected_assets,
         first_seen, last_updated, trend, confidence, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            narrative.id,
            narrative.title,
            narrative.summary,
            narrative.risk_level.value,
            json.dumps([a.value for a in narrative.affected_assets]),
            narrative.first_seen.isoformat(),
            narrative.last_updated.isoformat(),
            narrative.trend,
            narrative.confidence,
        ),
    )

    # Save history snapshot
    conn.execute(
        """INSERT INTO narrative_history (narrative_id, timestamp, risk_level, trend, summary)
        VALUES (?, ?, ?, ?, ?)""",
        (
            narrative.id,
            datetime.utcnow().isoformat(),
            narrative.risk_level.value,
            narrative.trend,
            narrative.summary,
        ),
    )

    # Save signals
    for signal in narrative.signals:
        conn.execute(
            """INSERT OR IGNORE INTO signals (id, source, title, content, url, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                signal.id,
                signal.source.value,
                signal.title,
                signal.content,
                signal.url,
                signal.timestamp.isoformat(),
                json.dumps(signal.metadata),
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO narrative_signals (narrative_id, signal_id) VALUES (?, ?)",
            (narrative.id, signal.id),
        )

    conn.commit()
    conn.close()


def load_active_narratives() -> list[Narrative]:
    """Load all active narratives from the database."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM narratives WHERE active = 1 ORDER BY last_updated DESC"
    ).fetchall()

    narratives = []
    for row in rows:
        # Load associated signals
        signal_rows = conn.execute(
            """SELECT s.* FROM signals s
            JOIN narrative_signals ns ON s.id = ns.signal_id
            WHERE ns.narrative_id = ?""",
            (row["id"],),
        ).fetchall()

        signals = [
            Signal(
                id=sr["id"],
                source=SignalSource(sr["source"]),
                title=sr["title"],
                content=sr["content"],
                url=sr["url"] or "",
                timestamp=datetime.fromisoformat(sr["timestamp"]),
                metadata=json.loads(sr["metadata"]) if sr["metadata"] else {},
            )
            for sr in signal_rows
        ]

        narratives.append(
            Narrative(
                id=row["id"],
                title=row["title"],
                summary=row["summary"],
                risk_level=RiskLevel(row["risk_level"]),
                affected_assets=[AssetClass(a) for a in json.loads(row["affected_assets"])],
                signals=signals,
                first_seen=datetime.fromisoformat(row["first_seen"]),
                last_updated=datetime.fromisoformat(row["last_updated"]),
                trend=row["trend"],
                confidence=row["confidence"],
            )
        )

    conn.close()
    return narratives


def get_narrative_history(narrative_id: str) -> list[dict]:
    """Get the evolution history of a narrative."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM narrative_history WHERE narrative_id = ? ORDER BY timestamp ASC",
        (narrative_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
