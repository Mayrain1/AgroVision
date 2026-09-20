import base64
import json
import os
from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError
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
        "calculation": {"type": "null"},
        "follow_up_question": {"type": "string"},
    },
    "required": ["problem", "solutions", "calculation", "follow_up_question"],
}


class AnalyzeRequest(BaseModel):
    crop: str
    description: str


class Problem(BaseModel):
    name: str
    confidence: float


class AnalyzeResponse(BaseModel):
    problem: Problem
    solutions: List[str]
    calculation: None = None
    follow_up_question: str


def get_openai_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set on the backend server.",
        )

    return OpenAI()


def validate_text_payload(crop: str, description: str) -> AnalyzeRequest:
    try:
        return AnalyzeRequest.model_validate(
            {
                "crop": crop,
                "description": description,
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Crop and description are required.",
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


def build_input(crop: str, description: str, image_data_url: str | None = None):
    prompt = (
        f"Crop: {crop}\n"
        f"Description: {description}\n\n"
        "Analyze the plant image when provided together with the crop name and "
        "symptom description. Provide a preliminary likely problem, confidence "
        "from 0 to 1, practical next steps, calculation as null, and one "
        "follow-up question. If the image is not informative enough, say so in "
        "the result and ask for the most useful next detail or photo."
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


def request_openai_analysis(payload: AnalyzeRequest, image_data_url: str | None = None) -> AnalyzeResponse:
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
                "for lab or field diagnostics."
            ),
            input=build_input(payload.crop, payload.description, image_data_url),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "agrovision_analysis",
                    "strict": True,
                    "schema": ANALYZE_SCHEMA,
                }
            },
        )

        data = json.loads(response.output_text)
        return AnalyzeResponse.model_validate(data)

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
        )

        image = form.get("image")
        if not isinstance(image, UploadFile):
            raise HTTPException(
                status_code=400,
                detail="Plant image is required.",
            )

        image_data_url = await read_image_upload(image)
        return request_openai_analysis(payload, image_data_url)

    if content_type.startswith("application/json"):
        try:
            payload = AnalyzeRequest.model_validate(await request.json())
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Crop and description are required.",
            ) from exc

        return request_openai_analysis(payload)

    raise HTTPException(
        status_code=415,
        detail="Unsupported request type. Use multipart/form-data.",
    )


@app.get("/api/weather", response_model=WeatherContextResponse)
def get_weather(city: str | None = None, latitude: float | None = None, longitude: float | None = None) -> WeatherContextResponse:
    if city is not None:
        try:
            latitude, longitude = get_coordinates_for_city(city)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=422,
            detail="Either city or both latitude and longitude must be provided.",
        )

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=422,
            detail="Latitude must be between -90 and 90, longitude between -180 and -180.",
        )

    try:
        return get_weather_context(latitude=latitude, longitude=longitude)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
