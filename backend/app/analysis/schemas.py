from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Category(StrEnum):
    study = "study"
    social = "social"
    exercise = "exercise"
    culture = "culture"
    daily = "daily"


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    keywords: list[str] = Field(min_length=1, max_length=5)
    summary: str = Field(min_length=1, max_length=300)
