from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .schemas import Lesson


class DevelopmentCard(BaseModel):
    character: str = Field(min_length=1, max_length=1)
    meaning_th: str
    onyomi: list[str]
    kunyomi: list[str]
    romaji: str
    strokes: int | None
    component: str
    note_th: str
    source_url: str
    review_status: Literal[
        "verified_sample", "sample", "published", "needs_review", "draft", "verified"
    ]


class DevelopmentLesson(Lesson):
    kanjis: list[DevelopmentCard]
    introduction_th: str
    provenance: str = Field(default="", exclude=True)
    sections: list[dict] = Field(default_factory=list)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerInput(Input):
    submission_id: UUID
    answer: str = Field(max_length=2000)


class ChoiceInput(Input):
    option_id: str = Field(min_length=1, max_length=80)


class ProgressInput(Input):
    progress: int = Field(ge=0, le=100)
    expected_version: int = Field(ge=0)


class ReviewInput(Input):
    knew: bool
    expected_version: int = Field(ge=0)


class GuestReview(Input):
    interval: int = Field(ge=1, le=90)
    due: datetime
    reviews: int = Field(ge=1, le=1000000)
    lapses: int = Field(ge=0, le=1000000)

    @field_validator("due")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timezone required")
        return value

    @model_validator(mode="after")
    def counts(self):
        if self.lapses > self.reviews:
            raise ValueError("Invalid review counts")
        return self


class GuestAttempt(AnswerInput):
    question_key: str = Field(max_length=200)


class GuestSnapshot(Input):
    cards: dict[str, GuestReview] = Field(default_factory=dict, max_length=500)
    lessons: dict[str, int] = Field(default_factory=dict, max_length=30)
    attempts: list[GuestAttempt] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def unique_valid(self):
        if any(len(char) != 1 for char in self.cards) or any(
            p not in range(101) for p in self.lessons.values()
        ):
            raise ValueError("Invalid guest progress")
        if len({a.submission_id for a in self.attempts}) != len(self.attempts):
            raise ValueError("Duplicate guest submission")
        return self


class SyncInput(Input):
    guest: GuestSnapshot
    snapshot: str = Field(max_length=64)
    choices: dict[str, Literal["guest", "cloud"]] = Field(max_length=730)
