"""Source-grounded comparison assessment; no generated model answers or fuzzy grading."""

import unicodedata


def comparison_rubric(chapter):
    # C always references the first comparison in this edition. Verify the prompt
    # contains both targets rather than guessing if a future edition changes it.
    pair = chapter.comparisons[0]
    if not all(side.kanji in chapter.exercise_c_prompt for side in pair):
        raise ValueError("C prompt does not identify its source comparison")
    tips = [
        {"id": f"tip-{i}", "text": tip, "json_pointer": f"/memory_tips/{i}"}
        for i, tip in enumerate(chapter.memory_tips)
        if all(side.kanji in tip for side in pair)
    ]
    return {
        "version": 1,
        "mode": "manual_source_grounded",
        "auto_scorable": False,
        "max_score": 1,
        "targets": [side.kanji for side in pair],
        "source_pairs": [side.model_dump() for side in pair],
        "source_tips": tips,
        "source_note": chapter.answer_c_note,
        "pdf_pages": [chapter.pdf_pages.comparison, chapter.pdf_pages.answer_key],
        "criterion": "One distinguishing visual feature supported by the cited source; a meaning or reading alone does not satisfy the visual-difference prompt.",
        "missing_specific_tip": not tips,
    }


def assess_comparison(response: str, rubric: dict):
    if rubric.get("mode") != "manual_source_grounded" or rubric.get("auto_scorable") is not False:
        raise ValueError("Unsupported comparison rubric")
    normalized = unicodedata.normalize("NFC", response).strip()
    return {
        "status": "needs_manual_review" if normalized else "unanswered",
        "score": None,
        "max_score": rubric["max_score"],
        "source_quote_match": any(
            normalized == unicodedata.normalize("NFC", tip["text"]).strip()
            for tip in rubric["source_tips"]
        )
        if normalized
        else False,
        "reason": "Source comparison notes do not provide an approved automatic answer key.",
    }
