import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class WeatherGeocodingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("main.get_coordinates_for_city")
    @patch("main.get_weather_context")
    def test_weather_endpoint_accepts_city_name(self, mock_get_weather_context, mock_get_coordinates_for_city):
        mock_get_coordinates_for_city.return_value = (49.95, 82.6)
        mock_get_weather_context.return_value = {
            "historical": {
                "period_days": 14,
                "average_temperature": 10.0,
                "total_precipitation": 5.0,
                "average_humidity": 60.0,
            },
            "forecast": {
                "period_days": 7,
                "average_temperature": 12.0,
                "total_precipitation": 4.0,
            },
        }

        response = self.client.get("/api/weather", params={"city": "Усть-Каменогорск"})

        self.assertEqual(response.status_code, 200)
        mock_get_coordinates_for_city.assert_called_once_with("Усть-Каменогорск")
        mock_get_weather_context.assert_called_once_with(latitude=49.95, longitude=82.6)

    @patch("main.get_coordinates_for_city")
    def test_weather_endpoint_returns_clear_error_for_unknown_city(self, mock_get_coordinates_for_city):
        mock_get_coordinates_for_city.side_effect = ValueError("City not found. Please check the spelling and try again.")

        response = self.client.get("/api/weather", params={"city": "Неизвестный город"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("City not found", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
