import { useEffect, useState } from "react";

const WEATHER_API_URL = "http://localhost:8000/api/weather";

function WeatherMetric({ icon, label, value, unit }) {
  return (
    <div className="weather-metric">
      <span className="metric-icon" aria-hidden="true">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value} {unit}</strong>
      </div>
    </div>
  );
}

function WeatherPanel({ city }) {
  const [weather, setWeather] = useState(null);
  const [weatherError, setWeatherError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!city.trim()) {
      setWeather(null);
      setWeatherError("");
      return;
    }

    let isCurrentRequest = true;

    async function loadWeather() {
    setWeatherError("");
    setWeather(null);
    setIsLoading(true);

    try {
      const params = new URLSearchParams({ city });
      const response = await fetch(`${WEATHER_API_URL}?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Backend вернул ошибку погоды.");
      }
      const weatherData = await response.json();
      if (isCurrentRequest) setWeather(weatherData);
    } catch (requestError) {
      if (isCurrentRequest) {
        setWeatherError(
          requestError.message ||
            "Не удалось получить погоду. Проверьте, что backend запущен."
        );
      }
    } finally {
      if (isCurrentRequest) setIsLoading(false);
    }
    }

    loadWeather();
    return () => {
      isCurrentRequest = false;
    };
  }, [city]);

  return (
    <section className="content-section weather-section" aria-labelledby="weather-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Условия выращивания</p>
          <h2 id="weather-title">Погодный контекст</h2>
        </div>
        <span className="section-number">02</span>
      </div>

      <p className="weather-location">
        {isLoading ? "Загружаем погоду для " : "Погода для "}
        <strong>{city || "указанного региона"}</strong>
      </p>

      {weatherError && <p className="error weather-error">{weatherError}</p>}

      {weather && (
        <div className="weather-results">
          <div className="weather-period">
            <div className="period-heading">
              <h3>Последние 14 дней</h3>
              <span>История</span>
            </div>
            <div className="weather-metrics">
              <WeatherMetric icon="T" label="Средняя температура" value={weather.historical.average_temperature} unit="°C" />
              <WeatherMetric icon="R" label="Осадки" value={weather.historical.total_precipitation} unit="мм" />
              <WeatherMetric icon="H" label="Средняя влажность" value={weather.historical.average_humidity} unit="%" />
            </div>
          </div>
          <div className="weather-period">
            <div className="period-heading">
              <h3>Следующие 7 дней</h3>
              <span>Прогноз</span>
            </div>
            <div className="weather-metrics">
              <WeatherMetric icon="T" label="Средняя температура" value={weather.forecast.average_temperature} unit="°C" />
              <WeatherMetric icon="R" label="Осадки" value={weather.forecast.total_precipitation} unit="мм" />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default WeatherPanel;