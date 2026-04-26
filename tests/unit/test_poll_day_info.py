"""Unit tests for core/helpers/poll_day_info.py."""

from datetime import date, datetime, time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from core.helpers import poll_day_info
from core.helpers.poll_day_info import (
    AUSTIN_TZ,
    _summarize_periods_for_date,
    get_poll_day_info,
    get_sunrise,
    get_weather,
)


@pytest.fixture(autouse=True)
def reset_caches():
    poll_day_info._reset_caches_for_test()
    yield
    poll_day_info._reset_caches_for_test()


class TestSunrise:
    def test_sunrise_returns_time_object(self):
        result = get_sunrise(date(2026, 6, 21))
        assert isinstance(result, time)

    def test_sunrise_summer_solstice_austin_around_630_am(self):
        # Austin sunrise on summer solstice is ~6:30 AM local time.
        result = get_sunrise(date(2026, 6, 21))
        assert 6 <= result.hour <= 7

    def test_sunrise_winter_solstice_austin_around_730_am(self):
        # Austin sunrise on winter solstice is ~7:20 AM local time.
        result = get_sunrise(date(2026, 12, 21))
        assert 7 <= result.hour <= 8

    def test_sunrise_is_deterministic(self):
        a = get_sunrise(date(2026, 4, 15))
        b = get_sunrise(date(2026, 4, 15))
        assert a == b


def _make_period(start: datetime, is_daytime: bool, **overrides):
    base = {
        "startTime": start.isoformat(),
        "isDaytime": is_daytime,
        "temperature": 78 if is_daytime else 62,
        "temperatureUnit": "F",
        "shortForecast": "Sunny" if is_daytime else "Clear",
        "detailedForecast": "Lots of sun.",
        "probabilityOfPrecipitation": {"value": 10},
        "icon": "https://example.com/icon.png",
    }
    base.update(overrides)
    return base


class TestSummarizePeriodsForDate:
    def test_returns_none_when_no_match(self):
        target = date(2026, 5, 10)
        periods = [
            _make_period(datetime(2026, 5, 1, 6, tzinfo=AUSTIN_TZ), True),
        ]
        assert _summarize_periods_for_date(periods, target) is None

    def test_pairs_day_and_night_for_target_date(self):
        target = date(2026, 5, 10)
        periods = [
            _make_period(
                datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ),
                True,
                temperature=85,
                shortForecast="Mostly Sunny",
                probabilityOfPrecipitation={"value": 20},
            ),
            _make_period(
                datetime(2026, 5, 10, 19, tzinfo=AUSTIN_TZ),
                False,
                temperature=64,
            ),
        ]
        result = _summarize_periods_for_date(periods, target)
        assert result == {
            "high": 85,
            "low": 64,
            "unit": "F",
            "short_forecast": "Mostly Sunny",
            "detailed_forecast": "Lots of sun.",
            "precip_chance": 20,
            "icon": "https://example.com/icon.png",
        }

    def test_handles_only_night_period(self):
        target = date(2026, 5, 10)
        periods = [
            _make_period(datetime(2026, 5, 10, 19, tzinfo=AUSTIN_TZ), False, temperature=58),
        ]
        result = _summarize_periods_for_date(periods, target)
        assert result is not None
        assert result["high"] is None
        assert result["low"] == 58

    def test_handles_missing_precip_value(self):
        target = date(2026, 5, 10)
        periods = [
            _make_period(
                datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ),
                True,
                probabilityOfPrecipitation={"value": None},
            ),
        ]
        result = _summarize_periods_for_date(periods, target)
        assert result is not None
        assert result["precip_chance"] is None

    def test_skips_malformed_period(self):
        target = date(2026, 5, 10)
        periods = [
            {"startTime": "not-a-date", "isDaytime": True, "temperature": 80},
            _make_period(datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ), True),
        ]
        result = _summarize_periods_for_date(periods, target)
        assert result is not None
        assert result["high"] == 78


def _mock_httpx_client(points_payload, forecast_payload):
    client = MagicMock()
    points_resp = MagicMock()
    points_resp.json.return_value = points_payload
    points_resp.raise_for_status.return_value = None
    forecast_resp = MagicMock()
    forecast_resp.json.return_value = forecast_payload
    forecast_resp.raise_for_status.return_value = None
    client.get.side_effect = [points_resp, forecast_resp]
    cm = MagicMock()
    cm.__enter__.return_value = client
    cm.__exit__.return_value = False
    return cm


class TestGetWeather:
    def test_returns_summary_for_date_in_window(self):
        target = date(2026, 5, 10)
        points_payload = {
            "properties": {"forecast": "https://api.weather.gov/gridpoints/EWX/156,90/forecast"}
        }
        forecast_payload = {
            "properties": {
                "periods": [
                    _make_period(datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ), True, temperature=82),
                    _make_period(
                        datetime(2026, 5, 10, 19, tzinfo=AUSTIN_TZ), False, temperature=66
                    ),
                ]
            }
        }
        with patch.object(
            poll_day_info.httpx,
            "Client",
            return_value=_mock_httpx_client(points_payload, forecast_payload),
        ):
            result = get_weather(target)
        assert result is not None
        assert result["high"] == 82
        assert result["low"] == 66

    def test_returns_none_outside_forecast_window(self):
        target = date(2030, 1, 1)
        points_payload = {
            "properties": {"forecast": "https://api.weather.gov/gridpoints/EWX/156,90/forecast"}
        }
        forecast_payload = {
            "properties": {
                "periods": [
                    _make_period(datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ), True),
                ]
            }
        }
        with patch.object(
            poll_day_info.httpx,
            "Client",
            return_value=_mock_httpx_client(points_payload, forecast_payload),
        ):
            result = get_weather(target)
        assert result is None

    def test_returns_none_on_http_error(self):
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("nope")
        cm = MagicMock()
        cm.__enter__.return_value = client
        cm.__exit__.return_value = False
        with patch.object(poll_day_info.httpx, "Client", return_value=cm):
            result = get_weather(date(2026, 5, 10))
        assert result is None

    def test_caches_forecast_response(self):
        target = date(2026, 5, 10)
        points_payload = {
            "properties": {"forecast": "https://api.weather.gov/gridpoints/EWX/156,90/forecast"}
        }
        forecast_payload = {
            "properties": {
                "periods": [
                    _make_period(datetime(2026, 5, 10, 6, tzinfo=AUSTIN_TZ), True),
                    _make_period(datetime(2026, 5, 10, 19, tzinfo=AUSTIN_TZ), False),
                ]
            }
        }
        client_mock = MagicMock()
        with patch.object(
            poll_day_info.httpx, "Client", return_value=client_mock
        ) as client_factory:
            client_mock.__enter__.return_value = MagicMock(
                get=MagicMock(
                    side_effect=[
                        MagicMock(
                            json=MagicMock(return_value=points_payload),
                            raise_for_status=MagicMock(),
                        ),
                        MagicMock(
                            json=MagicMock(return_value=forecast_payload),
                            raise_for_status=MagicMock(),
                        ),
                    ]
                )
            )
            client_mock.__exit__.return_value = False
            get_weather(target)
            # Second call should use cache, not re-instantiate the HTTP client.
            get_weather(target)
            assert client_factory.call_count == 1


class TestGetPollDayInfo:
    def test_includes_sunrise_and_date_even_when_weather_unavailable(self):
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("nope")
        cm = MagicMock()
        cm.__enter__.return_value = client
        cm.__exit__.return_value = False
        with patch.object(poll_day_info.httpx, "Client", return_value=cm):
            result = get_poll_day_info(date(2026, 5, 10))
        assert result["date"] == date(2026, 5, 10)
        assert isinstance(result["sunrise"], time)
        assert result["weather"] is None
