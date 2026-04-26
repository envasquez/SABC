"""Sunrise + weather forecast for tournament poll days.

Sunrise is computed locally with `astral` (no API). Weather is pulled from the
National Weather Service public API and cached in-memory for 30 minutes.
"""

from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from astral import LocationInfo
from astral.sun import sun

from core.helpers.logging import get_logger

logger = get_logger(__name__)

AUSTIN_LAT = 30.2672
AUSTIN_LON = -97.7431
AUSTIN_TZ = ZoneInfo("America/Chicago")
NWS_USER_AGENT = "SABC-Tournament-App (https://github.com/envasquez/SABC)"
NWS_BASE = "https://api.weather.gov"
FORECAST_TTL = timedelta(minutes=30)
HTTP_TIMEOUT = 5.0

_austin_location = LocationInfo("Austin", "USA", "America/Chicago", AUSTIN_LAT, AUSTIN_LON)

_forecast_cache: Dict[str, Any] = {"periods": None, "fetched_at": None}
_forecast_url_cache: Optional[str] = None


def get_sunrise(target_date: date_cls) -> time:
    s = sun(_austin_location.observer, date=target_date, tzinfo=AUSTIN_TZ)
    return s["sunrise"].astimezone(AUSTIN_TZ).time()


def _get_forecast_url(client: httpx.Client) -> str:
    global _forecast_url_cache
    if _forecast_url_cache is not None:
        return _forecast_url_cache
    resp = client.get(f"{NWS_BASE}/points/{AUSTIN_LAT},{AUSTIN_LON}", timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    url: str = resp.json()["properties"]["forecast"]
    _forecast_url_cache = url
    return url


def _fetch_forecast_periods() -> Optional[List[Dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    fetched_at = _forecast_cache.get("fetched_at")
    if fetched_at and now - fetched_at < FORECAST_TTL:
        cached: Optional[List[Dict[str, Any]]] = _forecast_cache.get("periods")
        return cached

    headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}
    try:
        with httpx.Client(headers=headers) as client:
            forecast_url = _get_forecast_url(client)
            resp = client.get(forecast_url, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            periods = resp.json()["properties"]["periods"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.warning(f"NWS forecast fetch failed: {e}")
        # Serve stale cache on failure if we have any, else None.
        stale: Optional[List[Dict[str, Any]]] = _forecast_cache.get("periods")
        return stale

    _forecast_cache["periods"] = periods
    _forecast_cache["fetched_at"] = now
    return periods


def _summarize_periods_for_date(
    periods: List[Dict[str, Any]], target_date: date_cls
) -> Optional[Dict[str, Any]]:
    day_period: Optional[Dict[str, Any]] = None
    night_period: Optional[Dict[str, Any]] = None
    for p in periods:
        try:
            start_local = datetime.fromisoformat(p["startTime"]).astimezone(AUSTIN_TZ).date()
        except (KeyError, ValueError):
            continue
        if start_local != target_date:
            continue
        if p.get("isDaytime"):
            day_period = p
        else:
            night_period = p

    if day_period is None and night_period is None:
        return None

    primary = day_period or night_period
    assert primary is not None
    precip = (primary.get("probabilityOfPrecipitation") or {}).get("value")
    return {
        "high": day_period["temperature"] if day_period else None,
        "low": night_period["temperature"] if night_period else None,
        "unit": primary.get("temperatureUnit", "F"),
        "short_forecast": primary.get("shortForecast"),
        "detailed_forecast": primary.get("detailedForecast"),
        "precip_chance": precip,
        "icon": primary.get("icon"),
    }


def get_weather(target_date: date_cls) -> Optional[Dict[str, Any]]:
    """Returns forecast summary for `target_date`, or None if outside the window
    or NWS is unreachable."""
    periods = _fetch_forecast_periods()
    if not periods:
        return None
    return _summarize_periods_for_date(periods, target_date)


def get_poll_day_info(target_date: date_cls) -> Dict[str, Any]:
    return {
        "date": target_date,
        "sunrise": get_sunrise(target_date),
        "weather": get_weather(target_date),
    }


def _reset_caches_for_test() -> None:
    global _forecast_url_cache
    _forecast_url_cache = None
    _forecast_cache["periods"] = None
    _forecast_cache["fetched_at"] = None
