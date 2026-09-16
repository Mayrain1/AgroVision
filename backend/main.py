import json
import os
from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

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


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_crop(payload: AnalyzeRequest) -> AnalyzeResponse:
    client = get_openai_client()

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            instructions=(
                "You are AgroVision, an assistant for preliminary crop health "
                "analysis. Analyze the user's crop and symptom description. "
                "Return only the structured JSON requested by the schema. "
                "Do not claim certainty; this is not a replacement for lab or "
                "field diagnostics."
            ),
            input=(
                f"Crop: {payload.crop}\n"
                f"Description: {payload.description}\n\n"
                "Provide a likely problem, confidence from 0 to 1, practical "
                "next steps, calculation as null, and one follow-up question."
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

        data = json.loads(response.output_text)
        return AnalyzeResponse.model_validate(data)

    except (APIConnectionError, APITimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API is currently unavailable. Please try again later.",
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI API request failed. Please check backend logs and try again.",
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI SDK request failed. Please check backend configuration.",
        ) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an invalid analysis format.",
        ) from exc
