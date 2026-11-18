"""Strict models for the immutable authoring-source JSON, not PDF extraction."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1)]
Page = Annotated[int, Field(ge=1, le=243)]


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Preview(SourceModel):
    character: Annotated[str, Field(min_length=1, max_length=1)]
    meaning_th: Text


class Card(Preview):
    reading_example: Text
    example: Text
    memory_note: Text
    pdf_page: Page


class Word(SourceModel):
    word: Text
    reading: Text
    meaning_th: Text
    pdf_page: Page


class Compared(SourceModel):
    kanji: Annotated[str, Field(min_length=1, max_length=1)]
    reading: Text
    meaning_th: Text


class DiagramCore(SourceModel):
    kanji: Annotated[str, Field(min_length=1, max_length=1)]
    label_th: Text


class DiagramRelated(SourceModel):
    kanji: Annotated[str, Field(min_length=1, max_length=1)]
    meaning_th: Text


class Diagram(SourceModel):
    core: DiagramCore | None
    related: list[DiagramRelated]
    comparison_pairs: list[list[Compared]]
    review_questions: list[Text]


class Answer(SourceModel):
    number: Annotated[int, Field(ge=1, le=14)]
    prompt: Text
    answer: Text
    pdf_page: Page


class Exercise(Answer):
    type: Literal["kanji_meaning", "vocabulary_reading"]


class Pages(SourceModel):
    start: Page
    end: Page
    opener: Page
    kanji_cards: list[Page]
    comparison: Page
    diagram: Page
    vocabulary: Page
    exercises: Page
    answer_key: Page


class Chapter(SourceModel):
    chapter: Annotated[int, Field(ge=1, le=30)]
    part: Annotated[int, Field(ge=1, le=6)]
    title_th: Text
    subtitle_th: Text
    pdf_pages: Pages
    category: Text
    kanji_preview: list[Preview]
    kanji_cards: list[Card]
    comparisons: list[list[Compared]]
    memory_tips: list[Text]
    diagram: Diagram
    vocabulary: list[Word]
    exercises: list[Exercise]
    answers: list[Answer]
    editorial_status: Literal["unverified_source_extraction"]
    exercise_c_prompt: Text
    answer_c_note: Text

    @model_validator(mode="after")
    def consistency(self):
        start = 11 + (self.chapter - 1) * 7
        p = self.pdf_pages
        if p.model_dump() != {
            "start": start,
            "end": start + 6,
            "opener": start,
            "kanji_cards": [start + 1, start + 2],
            "comparison": start + 3,
            "diagram": start + 4,
            "vocabulary": start + 5,
            "exercises": start + 6,
            "answer_key": 221 + (self.chapter - 1) // 2,
        }:
            raise ValueError("Chapter source-page boundaries do not reconcile")
        if self.part != (self.chapter - 1) // 5 + 1:
            raise ValueError("Chapter part does not reconcile")
        if len(self.kanji_cards) != 14 or len(self.vocabulary) != 8:
            raise ValueError("Incomplete chapter cards or vocabulary")
        if len(self.comparisons) != 3 or len(self.memory_tips) != 3:
            raise ValueError("Incomplete comparison or mnemonic content")
        if [c.character for c in self.kanji_cards] != [c.character for c in self.kanji_preview]:
            raise ValueError("Preview/card characters differ")
        if len({c.character for c in self.kanji_cards}) != 14:
            raise ValueError("Duplicate card within chapter")
        if len({(w.word, w.reading) for w in self.vocabulary}) != 8:
            raise ValueError("Duplicate vocabulary within chapter")
        if [q.number for q in self.exercises] != list(range(1, 15)) or [
            a.number for a in self.answers
        ] != list(range(1, 15)):
            raise ValueError("Missing or duplicate exercise/answer number")
        for q, a in zip(self.exercises, self.answers):
            if (q.prompt, q.answer) != (a.prompt, a.answer):
                raise ValueError("Exercise and answer key conflict")
            if q.pdf_page != p.exercises or a.pdf_page != p.answer_key:
                raise ValueError("Exercise/answer source page differs")
        if any(c.pdf_page != p.kanji_cards[i // 7] for i, c in enumerate(self.kanji_cards)):
            raise ValueError("Card source page differs")
        if any(w.pdf_page != p.vocabulary for w in self.vocabulary):
            raise ValueError("Vocabulary source page differs")
        if self.diagram.comparison_pairs != self.comparisons:
            raise ValueError("Diagram and comparison pairs differ")
        if any(len(pair) != 2 or pair[0].kanji == pair[1].kanji for pair in self.comparisons):
            raise ValueError("Invalid comparison pair")
        if len({r.kanji for r in self.diagram.related}) != len(self.diagram.related):
            raise ValueError("Duplicate diagram relationship")
        local = {c.character for c in self.kanji_cards}
        if (self.diagram.core and self.diagram.core.kanji not in local) or any(
            r.kanji not in local for r in self.diagram.related
        ):
            raise ValueError("Broken local diagram reference")
        if self.diagram.related and self.diagram.core is None:
            raise ValueError("Diagram related nodes require a source core")
        return self


class SourcePage(SourceModel):
    pdf_page: Page
    section: Text
    plain_text: Text


class Book(SourceModel):
    schema_version: Literal[2] = 2
    chapters: list[Chapter]
    pages: list[SourcePage]
    source_files: dict[str, str]
    source_metadata: dict
    issues: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def complete(self):
        if [c.chapter for c in self.chapters] != list(range(1, 31)):
            raise ValueError("All 30 chapters required exactly once in order")
        if [p.pdf_page for p in self.pages] != list(range(1, 244)):
            raise ValueError("All 243 source pages required exactly once in order")
        return self
