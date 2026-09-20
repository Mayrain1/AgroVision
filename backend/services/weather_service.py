from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from schemas.weather import (
    ForecastWeatherContext,
    HistoricalWeatherContext,
    WeatherContextResponse,
)


OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10
HISTORICAL_DAYS = 14
FORECAST_DAYS = 7


class WeatherServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_weather_context(latitude: float, longitude: float) -> WeatherContextResponse:
    today = date.today()
    historical_start = today - timedelta(days=HISTORICAL_DAYS)
    historical_end = today - timedelta(days=1)
    forecast_start = today + timedelta(days=1)
    forecast_end = today + timedelta(days=FORECAST_DAYS)

    historical_data = _request_open_meteo(
        OPEN_METEO_ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": historical_start.isoformat(),
            "end_date": historical_end.isoformat(),
            "hourly": "temperature_2m,precipitation,relative_humidity_2m",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "timezone": "auto",
        },
    )
    forecast_data = _request_open_meteo(
        OPEN_METEO_FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": forecast_start.isoformat(),
            "end_date": forecast_end.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "timezone": "auto",
        },
    )

    return WeatherContextResponse(
        historical=_build_historical_context(historical_data),
        forecast=_build_forecast_context(forecast_data),
    )


def _request_open_meteo(url: str, params: dict[str, Any]) -> dict[str, Any]:
    request_url = f"{url}?{urlencode(params)}"

    try:
        with urlopen(request_url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise WeatherServiceError("Open-Meteo returned an unexpected status.")

            return json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise WeatherServiceError("Open-Meteo request timed out.", status_code=504) from exc
    except HTTPError as exc:
        status_code = 400 if exc.code == 400 else 502
        raise WeatherServiceError("Open-Meteo rejected the weather request.", status_code=status_code) from exc
    except URLError as exc:
        raise WeatherServiceError("Open-Meteo is currently unavailable.", status_code=503) from exc
    except json.JSONDecodeError as exc:
        raise WeatherServiceError("Open-Meteo returned an invalid response.") from exc


def _build_historical_context(data: dict[str, Any]) -> HistoricalWeatherContext:
    hourly = _require_dict(data, "hourly")
    temperatures = _require_number_list(hourly, "temperature_2m")
    precipitation = _require_number_list(hourly, "precipitation")
    humidity = _require_number_list(hourly, "relative_humidity_2m")

    return HistoricalWeatherContext(
        period_days=HISTORICAL_DAYS,
        average_temperature=_round_one(_average(temperatures)),
        total_precipitation=_round_one(sum(precipitation)),
        average_humidity=_round_one(_average(humidity)),
    )


def _build_forecast_context(data: dict[str, Any]) -> ForecastWeatherContext:
    daily = _require_dict(data, "daily")
    temperatures = _require_number_list(daily, "temperature_2m_mean")
    precipitation = _require_number_list(daily, "precipitation_sum")

    return ForecastWeatherContext(
        period_days=FORECAST_DAYS,
        average_temperature=_round_one(_average(temperatures)),
        total_precipitation=_round_one(sum(precipitation)),
    )


def _require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise WeatherServiceError("Open-Meteo response is missing weather data.")

    return value


def _require_number_list(data: dict[str, Any], key: str) -> list[float]:
    value = data.get(key)
    if not isinstance(value, list):
        raise WeatherServiceError("Open-Meteo response has an invalid weather format.")

    numbers = [float(item) for item in value if isinstance(item, int | float)]
    if not numbers:
        raise WeatherServiceError("Open-Meteo response does not contain enough weather values.")

    return numbers


def _average(values: list[float]) -> float:
    return sum(values) / len(values)


def _round_one(value: float) -> float:
    return round(value, 1)
