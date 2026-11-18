import pytest

from app import seed as module


def test_rejects_a_duplicate_even_when_unique_glyph_count_is_unchanged(monkeypatch):
    monkeypatch.setattr(module, "SAMPLES", [*module.SAMPLES, module.SAMPLES[0]])
    with pytest.raises(ValueError, match="Invalid sample dataset"):
        module.validate_seed()


def test_rejects_duplicate_lesson_slugs(monkeypatch):
    lessons = list(module.LESSONS)
    lessons[1] = lessons[1].model_copy(update={"slug": lessons[0].slug})
    monkeypatch.setattr(module, "LESSONS", lessons)
    with pytest.raises(ValueError, match="identifiers/slugs"):
        module.validate_seed()


def test_rejects_duplicate_reading_within_a_kind(monkeypatch):
    samples = list(module.SAMPLES)
    samples[0] = samples[0].model_copy(update={"onyomi": ["モク", "モク"]})
    monkeypatch.setattr(module, "SAMPLES", samples)
    with pytest.raises(ValueError, match="Duplicate readings"):
        module.validate_seed()
