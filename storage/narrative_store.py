"""SQLite-backed persistence for narratives and signals."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from models.schemas import (
    AssetClass,
    AssetImpact,
    CascadingEffect,
    CounterNarrative,
    Narrative,
    RiskLevel,
    Signal,
    SignalSource,
    Signpost,
)

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
            signal_count INTEGER DEFAULT 0,
            FOREIGN KEY (narrative_id) REFERENCES narratives(id)
        );

        CREATE TABLE IF NOT EXISTS risk_score_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            score REAL NOT NULL,
            narrative_count INTEGER NOT NULL DEFAULT 0,
            top_narrative_title TEXT
        );
    """
    )
    conn.commit()

    # Migration: add signal_count to narrative_history for existing DBs
    try:
        conn.execute(
            "ALTER TABLE narrative_history ADD COLUMN signal_count INTEGER DEFAULT 0"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add asset_detail to narratives for existing DBs
    try:
        conn.execute(
            "ALTER TABLE narratives ADD COLUMN asset_detail TEXT DEFAULT '{}'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add cascading_effects to narratives for existing DBs
    try:
        conn.execute(
            "ALTER TABLE narratives ADD COLUMN cascading_effects TEXT DEFAULT '[]'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add counter_narrative to narratives for existing DBs
    try:
        conn.execute(
            "ALTER TABLE narratives ADD COLUMN counter_narrative TEXT DEFAULT 'null'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add signposts to narratives for existing DBs
    try:
        conn.execute(
            "ALTER TABLE narratives ADD COLUMN signposts TEXT DEFAULT '[]'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add assets_at_risk / assets_to_benefit columns
    for col, default in [("assets_at_risk", "'{}'"), ("assets_to_benefit", "'{}'")]:
        try:
            conn.execute(
                f"ALTER TABLE narratives ADD COLUMN {col} TEXT DEFAULT {default}"
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Migration: rename fixed_income -> credit in existing data
    conn.execute(
        "UPDATE narratives SET affected_assets = REPLACE(affected_assets, '\"fixed_income\"', '\"credit\"')"
    )
    conn.execute(
        "UPDATE narratives SET asset_detail = REPLACE(asset_detail, '\"fixed_income\"', '\"credit\"')"
    )
    conn.execute(
        "UPDATE risk_score_snapshots SET asset_class = 'credit' WHERE asset_class = 'fixed_income'"
    )
    conn.commit()

    conn.close()


def clear_narratives() -> None:
    """Deactivate all existing narratives before a fresh extraction."""
    conn = _get_conn()
    conn.execute("UPDATE narratives SET active = 0")
    conn.commit()
    conn.close()


def save_narrative(narrative: Narrative) -> None:
    """Save or update a narrative and its associated signals."""
    conn = _get_conn()

    def _serialize_impacts(d: dict[AssetClass, list[AssetImpact]]) -> str:
        return json.dumps(
            {a.value: [i.model_dump() for i in imps] for a, imps in d.items()}
        )

    conn.execute(
        """INSERT OR REPLACE INTO narratives
        (id, title, summary, risk_level, affected_assets, asset_detail,
         assets_at_risk, assets_to_benefit,
         cascading_effects, counter_narrative, signposts,
         first_seen, last_updated, trend, confidence, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            narrative.id,
            narrative.title,
            narrative.summary,
            narrative.risk_level.value,
            json.dumps([a.value for a in narrative.affected_assets]),
            "{}",  # legacy asset_detail — no longer used
            _serialize_impacts(narrative.assets_at_risk),
            _serialize_impacts(narrative.assets_to_benefit),
            json.dumps([e.model_dump() for e in narrative.cascading_effects]),
            json.dumps(narrative.counter_narrative.model_dump())
            if narrative.counter_narrative
            else "null",
            json.dumps([s.model_dump() for s in narrative.signposts]),
            narrative.first_seen.isoformat(),
            narrative.last_updated.isoformat(),
            narrative.trend,
            narrative.confidence,
        ),
    )

    # Save history snapshot
    conn.execute(
        """INSERT INTO narrative_history
        (narrative_id, timestamp, risk_level, trend, summary, signal_count)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            narrative.id,
            datetime.utcnow().isoformat(),
            narrative.risk_level.value,
            narrative.trend,
            narrative.summary,
            len(narrative.signals),
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

        # Deserialize assets_at_risk / assets_to_benefit
        def _load_impacts(col_name: str) -> dict[AssetClass, list[AssetImpact]]:
            raw_json = row[col_name] if col_name in row.keys() else "{}"
            raw = json.loads(raw_json) if raw_json else {}
            result: dict[AssetClass, list[AssetImpact]] = {}
            if not isinstance(raw, dict):
                return result
            for key, items in raw.items():
                try:
                    ac = AssetClass(key)
                except ValueError:
                    continue
                if isinstance(items, list):
                    impacts = []
                    for item in items:
                        if isinstance(item, dict) and "asset" in item:
                            impacts.append(
                                AssetImpact(
                                    asset=item["asset"],
                                    explanation=item.get("explanation", ""),
                                )
                            )
                        elif isinstance(item, str):
                            impacts.append(AssetImpact(asset=item, explanation=""))
                    if impacts:
                        result[ac] = impacts
            return result

        assets_at_risk = _load_impacts("assets_at_risk")
        assets_to_benefit = _load_impacts("assets_to_benefit")

        # Backward compat: migrate legacy asset_detail into assets_at_risk
        if not assets_at_risk and not assets_to_benefit:
            raw_detail = json.loads(row["asset_detail"]) if row["asset_detail"] else {}
            if isinstance(raw_detail, dict):
                for key, subs in raw_detail.items():
                    try:
                        ac = AssetClass(key)
                    except ValueError:
                        continue
                    if isinstance(subs, list):
                        assets_at_risk[ac] = [
                            AssetImpact(asset=s, explanation="") for s in subs
                        ]

        # Deserialize cascading_effects
        raw_effects = json.loads(row["cascading_effects"]) if row["cascading_effects"] else []
        cascading_effects = [
            CascadingEffect(**e) for e in raw_effects if isinstance(e, dict)
        ]

        # Deserialize counter_narrative
        raw_counter = row["counter_narrative"] if "counter_narrative" in row.keys() else "null"
        counter_obj = json.loads(raw_counter) if raw_counter else None
        counter_narrative = (
            CounterNarrative(**counter_obj)
            if isinstance(counter_obj, dict)
            else None
        )

        # Deserialize signposts
        raw_signposts = row["signposts"] if "signposts" in row.keys() else "[]"
        signposts = [
            Signpost(**s) for s in json.loads(raw_signposts or "[]") if isinstance(s, dict)
        ]

        narratives.append(
            Narrative(
                id=row["id"],
                title=row["title"],
                summary=row["summary"],
                risk_level=RiskLevel(row["risk_level"]),
                affected_assets=[AssetClass(a) for a in json.loads(row["affected_assets"])],
                assets_at_risk=assets_at_risk,
                assets_to_benefit=assets_to_benefit,
                cascading_effects=cascading_effects,
                counter_narrative=counter_narrative,
                signposts=signposts,
                signals=signals,
                first_seen=datetime.fromisoformat(row["first_seen"]),
                last_updated=datetime.fromisoformat(row["last_updated"]),
                trend=row["trend"],
                confidence=row["confidence"],
            )
        )

    conn.close()
    return narratives


def _title_word_overlap(a: str, b: str) -> float:
    """Compute word overlap ratio between two titles."""
    words_a = set(a.lower().strip().split())
    words_b = set(b.lower().strip().split())
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    return overlap / max(len(words_a), len(words_b))


def match_to_prior_narratives(
    new_narratives: list[Narrative], old_narratives: list[Narrative]
) -> None:
    """Match new narratives to prior ones by title similarity.

    If a match is found (>50% word overlap), copy the old narrative's id and
    first_seen to the new one so that narrative_history is continuous across
    refresh cycles. Modifies new_narratives in place.
    """
    if not old_narratives:
        return

    claimed: set[str] = set()
    for new_nar in new_narratives:
        best_score = 0.0
        best_match: Narrative | None = None
        for old_nar in old_narratives:
            if old_nar.id in claimed:
                continue
            score = _title_word_overlap(new_nar.title, old_nar.title)
            if score > best_score:
                best_score = score
                best_match = old_nar
        if best_match and best_score > 0.5:
            new_nar.id = best_match.id
            new_nar.first_seen = best_match.first_seen
            claimed.add(best_match.id)


def get_narrative_history(narrative_id: str) -> list[dict]:
    """Get the evolution history of a narrative."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM narrative_history WHERE narrative_id = ? ORDER BY timestamp ASC",
        (narrative_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_risk_score_snapshot(
    scores: dict[AssetClass, float],
    narratives: list[Narrative],
) -> None:
    """Persist current aggregate risk scores for time series tracking.

    Inserts one row per asset class with the current score, narrative count,
    and the title of the highest-risk narrative for that asset class.
    """
    conn = _get_conn()
    now = datetime.utcnow().isoformat()

    for asset_class, score in scores.items():
        # Find narratives affecting this asset class
        relevant = [n for n in narratives if asset_class in n.affected_assets]
        count = len(relevant)
        top_title = None
        if relevant:
            # Pick highest risk narrative for this asset class
            risk_order = {
                RiskLevel.CRITICAL: 4,
                RiskLevel.HIGH: 3,
                RiskLevel.MEDIUM: 2,
                RiskLevel.LOW: 1,
            }
            best = max(relevant, key=lambda n: risk_order.get(n.risk_level, 0))
            top_title = best.title

        conn.execute(
            """INSERT INTO risk_score_snapshots
            (timestamp, asset_class, score, narrative_count, top_narrative_title)
            VALUES (?, ?, ?, ?, ?)""",
            (now, asset_class.value, score, count, top_title),
        )

    conn.commit()
    conn.close()


def get_risk_score_history(
    asset_class: AssetClass | None = None,
    lookback_hours: int = 168,
) -> list[dict]:
    """Query risk score history for charting.

    Args:
        asset_class: Filter to a single asset class, or None for all.
        lookback_hours: How far back to look (default 7 days = 168h).

    Returns:
        List of dicts with timestamp, asset_class, score, narrative_count,
        top_narrative_title.
    """
    conn = _get_conn()
    cutoff = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat()

    if asset_class:
        rows = conn.execute(
            """SELECT * FROM risk_score_snapshots
            WHERE asset_class = ? AND timestamp >= ?
            ORDER BY timestamp ASC""",
            (asset_class.value, cutoff),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM risk_score_snapshots
            WHERE timestamp >= ?
            ORDER BY timestamp ASC""",
            (cutoff,),
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]
