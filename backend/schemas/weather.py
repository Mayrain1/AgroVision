from pydantic import BaseModel


class HistoricalWeatherContext(BaseModel):
    period_days: int
    average_temperature: float
    total_precipitation: float
    average_humidity: float


class ForecastWeatherContext(BaseModel):
    period_days: int
    average_temperature: float
    total_precipitation: float


class WeatherContextResponse(BaseModel):
    historical: HistoricalWeatherContext
    forecast: ForecastWeatherContext
