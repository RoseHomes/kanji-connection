from typing import Literal

from pydantic import BaseModel, Field


class Kanji(BaseModel):
    character: str = Field(min_length=1, max_length=1)
    meaning_th: str
    onyomi: list[str]
    kunyomi: list[str]
    romaji: str
    strokes: int | None
    component: str
    note_th: str
    source_url: str
    review_status: Literal["verified_sample", "sample", "published"] = "verified_sample"


class Lesson(BaseModel):
    id: int
    chapter: int | None = None
    slug: str
    part: int
    title_th: str
    summary_th: str
    anchors: list[str]
    status: Literal["sample", "needs_review", "published", "draft", "verified"] = "needs_review"
    difficulty: str = "ตามลำดับหลักสูตร"
    available_count: int = 0
    is_available: bool = False


class LessonDetail(Lesson):
    kanjis: list[Kanji]
    introduction_th: str
    provenance: str
    sections: list[dict] = Field(default_factory=list)


class VocabularyResponse(BaseModel):
    id: int
    written_form: str
    reading: str
    meaning_th: str
    romaji: str
    usage_notes: str


class ErrorDetail(BaseModel):
    code: str
    message: str
