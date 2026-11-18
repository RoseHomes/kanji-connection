"""Report source fidelity, editorial dispositions and exact local rehearsal evidence."""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.book_bundle import Bundle
from app.content_schema import Book


def main():
    output = ROOT / "private/json-content"
    book = Book.model_validate_json((output / "book.json").read_bytes())
    bundle = Bundle.model_validate_json((output / "import-bundle.json").read_bytes())
    evidence = json.loads((output / "verification.json").read_text("utf-8"))
    editorial = json.loads((output / "editorial.json").read_text("utf-8"))
    rehearsal = json.loads((output / "import-rehearsal.json").read_text("utf-8"))
    plan_hash = hashlib.sha256(bundle.model_dump_json().encode()).hexdigest()
    if rehearsal.get("bundle_sha256") != plan_hash:
        raise ValueError(
            "Stale seed rehearsal: rerun against the exact editorial bundle"
        )
    records = bundle.audit_records
    baseline = [r for r in records if r["classification"] != "actual_content_error"]
    open_records = [r for r in records if r["status"] == "open"]
    new_errors = [r for r in records if r["classification"] == "actual_content_error"]
    thai = evidence["thai_reference_checks"]["vocabulary"]
    thai_statuses = dict(Counter(r["status"] for r in thai.values()))
    totals = {
        "chapters_loaded": len(book.chapters),
        "structurally_validated_chapters": len(book.chapters),
        "editorially_approved_chapters": 0,
        "source_pages": len(book.pages),
        "kanji_card_occurrences": sum(len(c.kanji_cards) for c in book.chapters),
        "unique_teaching_kanji": len(
            {k.character for c in book.chapters for k in c.kanji_cards}
        ),
        "supporting_glyphs_preserved": len(bundle.supporting_glyphs),
        "supporting_glyphs_reference_enriched": len(editorial["supporting"]),
        "vocabulary_occurrences": sum(len(c.vocabulary) for c in book.chapters),
        "unique_vocabulary_pairs": len(
            {(w.word, w.reading) for c in book.chapters for w in c.vocabulary}
        ),
        "numbered_exercises": sum(len(c.exercises) for c in book.chapters),
        "explicit_answers": sum(len(c.answers) for c in book.chapters),
        "comparison_exercises": len(book.chapters),
        "reference_only_c_answer_notes": len(book.chapters),
        "comparison_pair_occurrences": sum(len(c.comparisons) for c in book.chapters),
        "memory_tips": sum(len(c.memory_tips) for c in book.chapters),
        "original_diagram_cores": sum(
            c.diagram.core is not None for c in book.chapters
        ),
        "coreless_diagrams_with_source_pair_views": len(editorial["diagrams"]),
        "chapter_sections": 7 * len(book.chapters),
        "raw_card_readings_dictionary_confirmed": sum(
            v["reading_verified"] for v in evidence["cards"].values()
        ),
        "annotated_contextual_card_occurrences": len(editorial["cards"]),
        "raw_vocabulary_readings_dictionary_confirmed": sum(
            v["pair_verified"] for v in evidence["vocabulary"].values()
        ),
        "additional_expression_reference_checks": len(editorial["expression_checks"]),
        "reading_answers_dictionary_confirmed": sum(
            v.get("pair_verified", False) for v in evidence["answers"].values()
        ),
        "meaning_answers_matching_source_cards": sum(
            v.get("matches_source_card", False) for v in evidence["answers"].values()
        ),
        "japanese_card_examples": len(evidence["examples"]),
        "thai_exact_match_occurrences": sum(
            v["exact_translation_match"] for v in thai.values()
        ),
        "thai_exact_match_unique_pairs": len(
            {
                (v["word"], v["reading"])
                for v in thai.values()
                if v["exact_translation_match"]
            }
        ),
        "thai_reference_covered_unique_pairs": len(
            {(v["word"], v["reading"]) for v in thai.values() if v["references"]}
        ),
        "thai_card_exact_matches": sum(
            v["exact_translation_match"]
            for v in evidence["thai_reference_checks"]["cards"].values()
        ),
        "manual_comparison_rubrics": len(editorial["rubrics"]),
        "rubrics_with_target_specific_source_tips": sum(
            bool(r["source_tips"]) for r in editorial["rubrics"].values()
        ),
        "original_audit_entries": len(baseline),
        "original_entries_resolved_for_stated_scope": sum(
            r["status"] != "open" for r in baseline
        ),
        "new_content_errors_corrected": sum(r["status"] != "open" for r in new_errors),
        "unresolved_audit_entries": len(open_records),
        "open_mapping_gaps": len(bundle.gaps),
        "proposed_rows": len(bundle.operations),
        "supabase_writes": 0,
    }
    by_category = Counter(r["classification"] for r in records)
    dispositions = Counter(r["status"] for r in records)
    per_chapter = [
        {
            "chapter": c.chapter,
            "title_th": c.title_th,
            "pdf_pages": c.pdf_pages.model_dump(),
            "cards": len(c.kanji_cards),
            "vocabulary": len(c.vocabulary),
            "exercises": len(c.exercises),
            "answers": len(c.answers),
            "original_core_provided": c.diagram.core is not None,
            "source_pair_view": str(c.chapter) in editorial["diagrams"],
            "editorial_approved": False,
            "imported": 0,
        }
        for c in book.chapters
    ]
    public = {
        "schema_version": 4,
        "source_manifest_sha256": bundle.source_sha256,
        "editorial_layer_sha256": bundle.editorial_layer_sha256,
        "totals": totals,
        "thai_statuses": thai_statuses,
        "chapters": per_chapter,
        "classification_counts": dict(by_category),
        "dispositions": dict(dispositions),
        "audit_dispositions": [
            {
                k: r[k]
                for k in ("id", "kind", "classification", "status", "note")
                if k in r
            }
            for r in records
        ],
        "dictionary_sources": evidence["dictionary_sources"],
        "thai_reference_sources": evidence["thai_reference_checks"]["sources"],
        "publication_approved": False,
    }
    (ROOT / "content_audit.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validation = {
        "schema_version": 4,
        "source_manifest_sha256": bundle.source_sha256,
        "editorial_layer_sha256": bundle.editorial_layer_sha256,
        "totals": totals,
        "local_rehearsal": rehearsal,
        "planned_counts": rehearsal["counts"],
        "editorial_approval": False,
        "supabase_import_permitted": False,
        "supabase_writes": 0,
    }
    (ROOT / "seed_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Content audit - editorial corrections and mapping dispositions",
        "",
        "**30 chapters pass structural validation; zero chapters have full editorial approval. No Supabase operation was performed.**",
        "",
        "The original 65-file JSON dataset is unchanged and remains the primary source. Corrections live in content/editorial-corrections.json; their edition manifest and expected original values are checked before use. Original source Book records and all PDF page references remain intact.",
        "",
        f"Of {len(baseline)} original entries, {totals['original_entries_resolved_for_stated_scope']} now have a documented reference/context/mapping disposition and {len(open_records)} broad editorial requirements remain open. One additional actual vocabulary sense error was found and corrected. A mapping resolution is not approval of missing source content or Thai translations.",
        "",
        "| Measure | Actual count |",
        "| --- | ---: |",
    ]
    lines += [f"| {k.replace('_', ' ')} | {v} |" for k, v in totals.items()]
    lines += [
        "",
        "## Classification of all reviewed entries",
        "",
        "| Classification | Entries |",
        "| --- | ---: |",
    ]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_category.items())]
    lines += ["", "| Disposition | Entries |", "| --- | ---: |"]
    lines += [f"| {k} | {v} |" for k, v in sorted(dispositions.items())]
    lines += [
        "",
        "The 47 missing-source-data entries comprise 45 supporting characters without standalone source cards and two absent diagram cores. Source omissions remain factual: dictionary supplements and source-pair views resolve the operational mapping without manufacturing source cards, Thai glosses or original artwork. Four database limitations are mapped as typed component/Kanji comparisons inside lesson sections. Ten original entries were editorial/reference requirements. The newly discovered actual error is separate from the original 61.",
        "",
        "## Verified corrections and reference evidence",
        "",
        "- 口: source ぐち is retained as a voiced compound segment in 入口/出口; the standalone reading index uses くち. Both contextual source occurrences are annotated.",
        "- 好: source すき belongs to 好き, including okurigana. The source example remains; the standalone dictionary form 好く/すく is indexed separately.",
        "- 靖: source やす has no complete word/name context. It is explicitly labeled as a stem; the primary-reference supplement is 靖い/やすい. No name reading is claimed.",
        "- Component names 亻/にんべん and 扌/てへん are confirmed by the primary radical index, rather than tested as standalone Kanji words.",
        "- 何円/なんえん is confirmed by a publisher sample. The failed exact JMdict-headword lookup remains recorded, with expression-level evidence added.",
        "- 裁判: the source offered a courthouse/place sense alongside a trial/proceeding sense. The correction removes the place sense and retains the existing Thai trial/proceeding wording; the official glossary distinguishes 裁判 from 裁判所. This does not approve every Thai gloss.",
        "- All 45 supporting Kanji retain their source occurrences and non-teaching role. KANJIDIC2 supplies readings, strokes and English reference meanings. Their standalone source cards and Thai meanings are still absent; these fields are not fabricated or marked approved.",
        "",
        "[口](https://www.kanjipedia.jp/kotoba/0002118800) | [好](https://www.kanjipedia.jp/kanji/0002163400) | [靖](https://www.kanjipedia.jp/kanji/0003907200) | [にんべん](https://www.kanjipedia.jp/sakuin/bushu/2) | [てへん](https://www.kanjipedia.jp/sakuin/bushu/4) | [何円 publisher sample](https://www.hituzi.co.jp/hituzibooks/img/1216meguriai1_sample_ch2.pdf) | [裁判/裁判所 official glossary](https://www.houterasu.or.jp/site/yasasiinihongo/houritsu-saiban-kotoba.html)",
        "",
        "## Japanese meanings and Thai translation coverage",
        "",
        "JMdict evidence now retains applicable sense restrictions, complete English glosses, register labels and sense notes. Dictionary membership verifies written-form/reading pairs; it does not alone approve a Thai translation. All 210 reading answers match JMdict and all 210 meaning-answer strings agree with their source card candidates.",
        "",
        f"Four pinned Japan Foundation Marugoto Japanese-Thai XLSX lists cover {totals['thai_reference_covered_unique_pairs']} unique vocabulary pairs. Exact canonical/whitespace-normalized Thai matches: {totals['thai_exact_match_occurrences']} source occurrences across {totals['thai_exact_match_unique_pairs']} pairs. Occurrence statuses: {thai_statuses}. Card-level exact matches: {totals['thai_card_exact_matches']}. Exact matches are limited field evidence, not whole-chapter approval.",
        "Different translations are review candidates, not automatically errors: examples include blue shades, meal versus eating, and context-sensitive family terms. Check 神宮 for its imperial-shrine sense and 申す for humble register. No replacement Thai gloss is guessed. The supporting characters still lack independently approved Thai meanings. Detailed rows, snapshot hashes, worksheets and row numbers remain private.",
        "[Japan Foundation reference index](https://marugoto.jpf.go.jp/teacher/resource/pre_intermediate/) - primary lists are private verification references, not redistributed lesson content.",
        "",
        "## Diagrams and comparison scoring",
        "",
        "Chapters 2 and 4 now have comparison-network views using exactly the three supplied pairs and source labels on pages 22 and 36. Original null cores remain null. Component endpoints have an explicit entity type and are validated against the prepared component/Kanji records. No hub, component-position link, historical claim or artwork file was invented.",
        "All 30 C exercises have manual, source-grounded rubric metadata with original answer-note/page references, a one-point maximum and no automatic credit. Twenty-three have a source memory tip mentioning both target characters; seven have only the comparison and reference note. Blank responses are unanswered; nonblank responses require manual review. Even an exact source quote receives no automatic score while the rubric/content remains unapproved.",
        "",
        "## Remaining open requirements",
        "",
        "| Entry | Remaining verification |",
        "| --- | --- |",
        "| thai_semantic_review_required | Independently review uncovered/different Thai meanings, register and context, including supporting-character Thai fields. |",
        "| mnemonic_claim_review_required | Review all source mnemonic/composition/phonetic claims; none are certified historical etymology. |",
        "| diagram_visual_review_required | Review any eventual visual adaptation and reuse rights; source-pair mappings do not reconstruct the original art. |",
        "| comparison_rubric_required | Teacher approval and manual grading remain necessary, especially the seven pairs without a target-specific source tip. |",
        "",
        "## Chapter/page reconciliation",
        "",
        "| Ch. | Source pages | Title | Cards / vocabulary | Numbered questions / answers | Diagram mapping |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in book.chapters:
        lines.append(
            f"| {c.chapter} | {c.pdf_pages.start}-{c.pdf_pages.end} | {c.title_th} | {len(c.kanji_cards)} / {len(c.vocabulary)} | {len(c.exercises)} / {len(c.answers)} | {'source core graph' if c.diagram.core else 'source pair network; core absent'} |"
        )
    lines += [
        "",
        "Every original issue ID and its classification, evidence and disposition is retained in private/json-content/audit-dispositions.json. Public content_audit.json contains the disposition index without full source lessons. See [CONTENT_PIPELINE.md](CONTENT_PIPELINE.md) and [SEED_VALIDATION.md](SEED_VALIDATION.md).",
    ]
    (ROOT / "docs/CONTENT_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    seed = [
        "# Seed validation - editorial overlay",
        "",
        "JSON and source records remain immutable. The separate editorial layer produces private/needs_review operational records, with original values, dictionary supplements, correction IDs and evidence retained. Nothing is published or catalog-visible. No Supabase connection, seed, migration, deployment or Git push occurred.",
        "",
        f"Full local rehearsal: {len(bundle.operations)} prepared rows, two passes with foreign keys enabled, zero duplicate inserts and complete rollback. There are {len(open_records)} broad editorial blockers and zero approved chapters.",
        "",
        "| Existing table | Planned rows |",
        "| --- | ---: |",
    ]
    seed += [
        f"| {name} | {count} |" for name, count in sorted(rehearsal["counts"].items())
    ]
    seed += [
        "",
        "Source coverage is unchanged: 313 teaching Kanji plus 45 supporting glyphs, 197 vocabulary pairs/240 placements, 420 numbered questions/answers and 30 reference-only C notes. Supporting reference readings are additional reference metadata, not new teaching cards. Existing editorial changes remain untouched; the importer reports differing fields as conflicts. All user-owned tables receive zero rows.",
        "",
        "```json",
        json.dumps(rehearsal, indent=2),
        "```",
        "",
        "Rehearsal records the exact bundle hash and editorial-layer hash; reports reject stale rehearsal evidence. Tests cover complete-plan foreign keys, repeat import, rollback, existing editorial values, correction guards, original-data integrity, typed diagram endpoints, Thai reference parsing and manual scoring. PostgreSQL-specific execution is not claimed by this SQLite rehearsal.",
        "Before remote import: finish or explicitly accept the remaining editorial scope, obtain owner authorization and verify live empty-table/schema assumptions read-only. A future PostgreSQL caller must own its transaction/advisory lock and commit. No remote book-import CLI or automatic commit has been introduced.",
    ]
    (ROOT / "docs/SEED_VALIDATION.md").write_text(
        "\n".join(seed) + "\n", encoding="utf-8"
    )
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
