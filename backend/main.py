import base64
import json
import os
from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError
from starlette.datastructures import UploadFile

from schemas.weather import WeatherContextResponse
from services.geocoding_service import get_coordinates_for_city
from services.weather_service import WeatherServiceError, get_weather_context

load_dotenv()
app = FastAPI(title="AgroVision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

ANALYZE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "problem": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["name", "confidence"],
        },
        "solutions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "calculation": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "needed": {"type": "boolean"},
                        "fertilizer": {"type": "string"},
                        "application_rate_kg_per_ha": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                        },
                    },
                    "required": [
                        "needed",
                        "fertilizer",
                        "application_rate_kg_per_ha",
                    ],
                },
            ]
        },
        "follow_up_question": {"type": "string"},
    },
    "required": ["problem", "solutions", "calculation", "follow_up_question"],
}


class AnalyzeRequest(BaseModel):
    crop: str
    description: str
    city: str
    area_ha: float | None = Field(default=None, gt=0)


class Problem(BaseModel):
    name: str
    confidence: float


class CalculationRecommendation(BaseModel):
    needed: bool
    fertilizer: str
    application_rate_kg_per_ha: float = Field(gt=0)


class Calculation(BaseModel):
    needed: bool
    fertilizer: str
    application_rate_kg_per_ha: float = Field(gt=0)
    area_ha: float = Field(gt=0)
    total_amount_kg: float = Field(gt=0)


class OpenAIAnalysisResponse(BaseModel):
    problem: Problem
    solutions: List[str]
    calculation: CalculationRecommendation | None = None
    follow_up_question: str


class AnalyzeResponse(BaseModel):
    problem: Problem
    solutions: List[str]
    calculation: Calculation | None = None
    follow_up_question: str


def get_openai_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set on the backend server.",
        )

    return OpenAI()


def validate_text_payload(
    crop: str,
    description: str,
    city: str,
    area_ha: str | None,
) -> AnalyzeRequest:
    try:
        return AnalyzeRequest.model_validate(
            {
                "crop": crop,
                "description": description,
                "city": city,
                "area_ha": area_ha or None,
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Crop, description, and city are required. Area must be a positive number.",
        ) from exc


async def read_image_upload(image: UploadFile) -> str:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format. Please upload JPG, PNG, or WEBP.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty.",
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image is too large. Maximum size is 5 MB.",
        )

    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{image.content_type};base64,{encoded_image}"


def build_input(
    crop: str,
    description: str,
    city: str,
    weather_context: WeatherContextResponse,
    area_ha: float | None = None,
    image_data_url: str | None = None,
):
    weather_context = WeatherContextResponse.model_validate(weather_context)
    historical = weather_context.historical
    forecast = weather_context.forecast
    area_line = f"Field area: {area_ha} ha\n" if area_ha is not None else ""
    prompt = (
        f"Crop: {crop}\n"
        f"Description: {description}\n\n"
        f"Location: {city}\n"
        f"{area_line}"
        "Historical weather, last 14 days:\n"
        f"- average temperature: {historical.average_temperature} °C\n"
        f"- total precipitation: {historical.total_precipitation} mm\n"
        f"- average humidity: {historical.average_humidity} %\n\n"
        "Forecast, next 7 days:\n"
        f"- average temperature: {forecast.average_temperature} °C\n"
        f"- total precipitation: {forecast.total_precipitation} mm\n\n"
        "Analyze the plant image when provided together with the crop name and "
        "symptom description. Weather is additional context, not proof of the "
        "cause of a disease. Use it cautiously when explaining possibilities. "
        "Provide a preliminary likely problem, confidence from 0 to 1, practical "
        "next steps, an optional fertilizer recommendation, and one "
        "follow-up question. If the image is not informative enough, say so in "
        "the result and ask for the most useful next detail or photo. "
        "Always write every user-facing field in Russian. If fertilizer is not "
        "appropriate, return calculation as null. Return only the application "
        "rate in kg/ha; do not calculate total amount. When field area is "
        "provided, give a fertilizer recommendation whenever it is reasonably "
        "appropriate for the identified problem; do not omit it merely because "
        "the area is present."
    )

    if not image_data_url:
        return prompt

    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": prompt,
                },
                {
                    "type": "input_image",
                    "image_url": image_data_url,
                    "detail": "auto",
                },
            ],
        }
    ]


def request_openai_analysis(
    payload: AnalyzeRequest,
    weather_context: WeatherContextResponse,
    image_data_url: str | None = None,
) -> AnalyzeResponse:
    client = get_openai_client()

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            instructions=(
                "You are AgroVision, an assistant for preliminary crop health "
                "analysis. Analyze the user's plant image, crop name, and "
                "symptom description. "
                "Return only the structured JSON requested by the schema. "
                "Do not claim certainty or invent details that cannot be "
                "determined from the image and text. This is not a replacement "
                "for lab or field diagnostics. Weather is only additional context, "
                "never proof of a disease cause. "
                "Always respond in Russian."
                "All fields in the structured response must contain Russian text."
                "Use Russian names for plant diseases and recommendations."
                "Scientific Latin names may be included in parentheses when useful."
            ),
            input=build_input(
                payload.crop,
                payload.description,
                payload.city,
                weather_context,
                payload.area_ha,
                image_data_url,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "agrovision_analysis",
                    "strict": True,
                    "schema": ANALYZE_SCHEMA,
                }
            },
        )

        data = OpenAIAnalysisResponse.model_validate(json.loads(response.output_text))
        calculation = None
        if data.calculation and data.calculation.needed and payload.area_ha is not None:
            calculation = Calculation(
                needed=True,
                fertilizer=data.calculation.fertilizer,
                application_rate_kg_per_ha=data.calculation.application_rate_kg_per_ha,
                area_ha=payload.area_ha,
                total_amount_kg=round(
                    payload.area_ha * data.calculation.application_rate_kg_per_ha,
                    2,
                ),
            )

        return AnalyzeResponse(
            problem=data.problem,
            solutions=data.solutions,
            calculation=calculation,
            follow_up_question=data.follow_up_question,
        )

    except (APIConnectionError, APITimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API is currently unavailable. Please try again later.",
        ) from exc
    except APIError as exc:
        print(f"OPENAI API ERROR: {exc}")
        raise HTTPException(
            status_code=502,
            detail="OpenAI API request failed.",
        ) from exc
    except OpenAIError as exc:
        print(f"OPENAI SDK ERROR: {exc}")
        raise HTTPException(
            status_code=502,
            detail="OpenAI SDK request failed.",
        ) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an invalid analysis format.",
        ) from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_crop(request: Request) -> AnalyzeResponse:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = validate_text_payload(
            crop=str(form.get("crop") or ""),
            description=str(form.get("description") or ""),
            city=str(form.get("city") or ""),
            area_ha=str(form.get("area_ha") or ""),
        )

        image = form.get("image")
        if not isinstance(image, UploadFile):
            raise HTTPException(
                status_code=400,
                detail="Plant image is required.",
            )

        image_data_url = await read_image_upload(image)
    weather_context = get_weather_for_city(payload.city)
    return request_openai_analysis(payload, weather_context, image_data_url)

    if content_type.startswith("application/json"):
        try:
            payload = AnalyzeRequest.model_validate(await request.json())
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Crop, description, and city are required. Area must be a positive number.",
            ) from exc

        weather_context = get_weather_for_city(payload.city)
        return request_openai_analysis(payload, weather_context)

    raise HTTPException(
        status_code=415,
        detail="Unsupported request type. Use multipart/form-data.",
    )


def get_weather_for_city(city: str) -> WeatherContextResponse:
    try:
        latitude, longitude = get_coordinates_for_city(city)
        return get_weather_context(latitude=latitude, longitude=longitude)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/api/weather", response_model=WeatherContextResponse)
async def weather_for_city(city: str = Query(..., min_length=1)) -> WeatherContextResponse:
    return get_weather_for_city(city)
