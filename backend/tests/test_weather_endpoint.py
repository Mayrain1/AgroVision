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

    @patch("main.OpenAI")
    @patch("main.get_weather_context")
    @patch("main.get_coordinates_for_city")
    def test_analyze_uses_weather_and_calculates_fertilizer(
        self,
        mock_get_coordinates_for_city,
        mock_get_weather_context,
        mock_openai,
    ):
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

        class FakeResponses:
            last_input = None

            def create(self, **kwargs):
                self.last_input = kwargs["input"]

                class FakeResponse:
                    output_text = (
                        '{"problem":{"name":"problem","confidence":0.8},'
                        '"solutions":["solution"],'
                        '"calculation":{"needed":true,"fertilizer":"fertilizer",'
                        '"application_rate_kg_per_ha":120},'
                        '"follow_up_question":"question"}'
                    )

                return FakeResponse()

        fake_responses = FakeResponses()
        mock_openai.return_value.responses = fake_responses

        response = self.client.post(
            "/api/analyze",
            data={
                "crop": "wheat",
                "description": "spots",
                "city": "Test City",
                "area_ha": "50",
            },
            files={"image": ("plant.jpg", b"fake-image", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["calculation"]["total_amount_kg"], 6000)
        prompt = fake_responses.last_input[0]["content"][0]["text"]
        self.assertIn("Historical weather, last 14 days", prompt)
        self.assertIn("average humidity: 60.0 %", prompt)
        mock_get_coordinates_for_city.assert_called_once_with("Test City")
        mock_get_weather_context.assert_called_once_with(latitude=49.95, longitude=82.6)


if __name__ == "__main__":
    unittest.main()
