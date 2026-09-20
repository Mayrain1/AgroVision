from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
REQUEST_TIMEOUT_SECONDS = 10
CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _city_candidates(city: str) -> list[str]:
    query = (city or "").strip()
    if not query:
        return []

    candidates = [query]
    if any(ord(ch) > 127 for ch in query):
        transliterated = "".join(CYRILLIC_TO_LATIN.get(ch.lower(), ch) for ch in query)
        candidates.append(transliterated)
        candidates.append(transliterated.replace(" ", "-"))

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in seen:
            unique.append(normalized)
            seen.add(normalized)
    return unique


def get_coordinates_for_city(city: str) -> tuple[float, float]:
    query = (city or "").strip()
    if not query:
        raise ValueError("City name is required.")

    last_error: ValueError | None = None
    for candidate in _city_candidates(query):
        for language in ("en", "ru"):
            request_url = f"{GEOCODING_URL}?{urlencode({
                'name': candidate,
                'count': 1,
                'language': language,
                'format': 'json',
            })}"

            try:
                with urlopen(request_url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    if response.status != 200:
                        raise ValueError("Unable to resolve the city right now.")

                    payload = json.loads(response.read().decode("utf-8"))
            except TimeoutError as exc:
                last_error = ValueError("Geocoding service timed out. Please try again later.")
                continue
            except HTTPError as exc:
                last_error = ValueError("City not found. Please check the spelling and try again.") if exc.code == 400 else ValueError("Geocoding service is unavailable right now.")
                continue
            except URLError as exc:
                last_error = ValueError("Geocoding service is unavailable right now.")
                continue
            except json.JSONDecodeError as exc:
                last_error = ValueError("Geocoding service returned an invalid response.")
                continue

            results = payload.get("results")
            if not isinstance(results, list) or not results:
                last_error = ValueError("City not found. Please check the spelling and try again.")
                continue

            first_result = results[0]
            if not isinstance(first_result, dict):
                last_error = ValueError("City not found. Please check the spelling and try again.")
                continue

            latitude = first_result.get("latitude")
            longitude = first_result.get("longitude")
            if latitude is None or longitude is None:
                last_error = ValueError("City not found. Please check the spelling and try again.")
                continue

            return float(latitude), float(longitude)

    if last_error is not None:
        raise last_error
    raise ValueError("City not found. Please check the spelling and try again.")
