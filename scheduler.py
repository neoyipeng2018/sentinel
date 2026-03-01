"""Background thread scheduler for periodic signal refresh.

Runs independently of Streamlit browser sessions so that risk score
time series accumulate even when no tab is open.
"""

import logging
import threading

from ai.chains.counter_narrative import generate_counter_narratives
from ai.chains.narrative_extractor import extract_narratives
from ai.chains.risk_assessor import compute_asset_risk_scores
from ai.chains.signpost_generator import generate_signposts
from ai.chains.trend_analyzer import compute_quantitative_trend
from ai.llm import get_llm
from config.overrides import get_custom_signals
from sources.market import detect_anomalies, fetch_market_data
from sources.news import fetch_news_signals
from sources.predictions import fetch_prediction_signals
from sources.social import fetch_reddit_signals
from storage.narrative_store import (
    clear_narratives,
    load_active_narratives,
    match_to_prior_narratives,
    save_narrative,
    save_risk_score_snapshot,
)

logger = logging.getLogger(__name__)

# Lock shared with app.py — prevents the manual button and background
# thread from running a refresh cycle concurrently.
refresh_lock = threading.Lock()

# Internal state guarded by _guard_lock
_guard_lock = threading.Lock()
_stop_event: threading.Event | None = None
_thread: threading.Thread | None = None


def run_refresh_cycle(prefer_free: bool = True) -> int:
    """Execute one full refresh cycle (no Streamlit dependency).

    Returns the number of narratives extracted.
    """
    signals = []
    signals.extend(fetch_news_signals())

    data = fetch_market_data()
    signals.extend(detect_anomalies(data))

    signals.extend(fetch_reddit_signals())

    signals.extend(fetch_prediction_signals())

    custom_fn = get_custom_signals()
    if custom_fn:
        signals.extend(custom_fn())

    if not signals:
        logger.info("No signals fetched — skipping extraction")
        return 0

    llm = get_llm(prefer_free=prefer_free)
    narratives = extract_narratives(signals, llm)

    # Generate counter-narratives before saving
    try:
        generate_counter_narratives(narratives, llm)
    except Exception:
        logger.exception("Counter-narrative generation failed — continuing without")

    # Generate risk signposts before saving
    try:
        generate_signposts(narratives, llm)
    except Exception:
        logger.exception("Signpost generation failed — continuing without")

    old_narratives = load_active_narratives()
    clear_narratives()
    match_to_prior_narratives(narratives, old_narratives)

    for nar in narratives:
        save_narrative(nar)
        trend = compute_quantitative_trend(nar.id, len(nar.signals))
        if trend:
            nar.trend = trend
            save_narrative(nar)

    scores = compute_asset_risk_scores(narratives)
    save_risk_score_snapshot(scores, narratives)

    logger.info("Refresh cycle complete — %d narratives", len(narratives))
    return len(narratives)


def _scheduler_loop(interval_seconds: float, stop_event: threading.Event) -> None:
    """Daemon thread target. Sleeps then refreshes in a loop."""
    logger.info("Scheduler started (interval=%ds)", interval_seconds)
    while not stop_event.is_set():
        stop_event.wait(interval_seconds)
        if stop_event.is_set():
            break
        try:
            with refresh_lock:
                run_refresh_cycle(prefer_free=True)
        except Exception:
            logger.exception("Scheduler refresh cycle failed")
    logger.info("Scheduler stopped")


def start_scheduler(interval_minutes: int = 60) -> None:
    """Start the background scheduler if it isn't already running."""
    global _stop_event, _thread
    with _guard_lock:
        if _thread is not None and _thread.is_alive():
            return  # already running
        _stop_event = threading.Event()
        _thread = threading.Thread(
            target=_scheduler_loop,
            args=(interval_minutes * 60, _stop_event),
            daemon=True,
            name="sentinel-scheduler",
        )
        _thread.start()
        logger.info("Scheduler thread launched")


def stop_scheduler() -> None:
    """Signal the background scheduler to stop."""
    global _stop_event, _thread
    with _guard_lock:
        if _stop_event is not None:
            _stop_event.set()
        if _thread is not None:
            _thread.join(timeout=5)
            _thread = None
        _stop_event = None
        logger.info("Scheduler thread stopped")
