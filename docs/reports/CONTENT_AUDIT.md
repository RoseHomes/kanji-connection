# Content audit - editorial corrections and mapping dispositions

**30 chapters pass structural validation; zero chapters have full editorial
approval.**

The unchanged 2,941-row edition was imported into Supabase as owner-authorized
**private staging** on 2026-11-16. All lessons remain needs_review/private and
catalog-hidden; all four open editorial requirements remain. Importing does not
confer educational approval. See
[the live import report](LIVE_PRIVATE_IMPORT_REPORT.md) for database and
learning checks.

The original 65-file JSON dataset is unchanged and remains the primary source.
Corrections live in content/editorial-corrections.json; their edition manifest
and expected original values are checked before use. Original source Book
records and all PDF page references remain intact.

Of 61 original entries, 57 now have a documented reference/context/mapping
disposition and 4 broad editorial requirements remain open. One additional
actual vocabulary sense error was found and corrected. A mapping resolution is
not approval of missing source content or Thai translations.

| Measure                                      | Actual count |
| -------------------------------------------- | -----------: |
| chapters loaded                              |           30 |
| structurally validated chapters              |           30 |
| editorially approved chapters                |            0 |
| source pages                                 |          243 |
| kanji card occurrences                       |          420 |
| unique teaching kanji                        |          313 |
| supporting glyphs preserved                  |           45 |
| supporting glyphs reference enriched         |           45 |
| vocabulary occurrences                       |          240 |
| unique vocabulary pairs                      |          197 |
| numbered exercises                           |          420 |
| explicit answers                             |          420 |
| comparison exercises                         |           30 |
| reference only c answer notes                |           30 |
| comparison pair occurrences                  |           90 |
| memory tips                                  |           90 |
| original diagram cores                       |           28 |
| coreless diagrams with source pair views     |            2 |
| chapter sections                             |          210 |
| raw card readings dictionary confirmed       |          416 |
| annotated contextual card occurrences        |            4 |
| raw vocabulary readings dictionary confirmed |          239 |
| additional expression reference checks       |            1 |
| reading answers dictionary confirmed         |          210 |
| meaning answers matching source cards        |          210 |
| japanese card examples                       |          254 |
| thai exact match occurrences                 |           73 |
| thai exact match unique pairs                |           61 |
| thai reference covered unique pairs          |           77 |
| thai card exact matches                      |           71 |
| manual comparison rubrics                    |           30 |
| rubrics with target specific source tips     |           23 |
| original audit entries                       |           61 |
| original entries resolved for stated scope   |           57 |
| new content errors corrected                 |            1 |
| unresolved audit entries                     |            4 |
| open mapping gaps                            |            0 |
| committed private book rows                  |         2941 |
| publicly visible lessons                     |            0 |

## Classification of all reviewed entries

| Classification               | Entries |
| ---------------------------- | ------: |
| actual_content_error         |       1 |
| database_mapping_limitation  |       4 |
| editorial_review_requirement |      10 |
| missing_source_data          |      47 |

| Disposition                 | Entries |
| --------------------------- | ------: |
| open                        |       4 |
| resolved_context            |       3 |
| resolved_correction         |       1 |
| resolved_mapping            |       6 |
| resolved_reference          |       3 |
| resolved_supporting_mapping |      45 |

The 47 missing-source-data entries comprise 45 supporting characters without
standalone source cards and two absent diagram cores. Source omissions remain
factual: dictionary supplements and source-pair views resolve the operational
mapping without manufacturing source cards, Thai glosses or original artwork.
Four database limitations are mapped as typed component/Kanji comparisons inside
lesson sections. Ten original entries were editorial/reference requirements. The
newly discovered actual error is separate from the original 61.

## Correction and reference methods

The overlay preserves four contextual reading occurrences: compound voicing, a
word with okurigana and an incomplete stem. Standalone indexes and source
examples have different scopes. Component names use radical references rather
than standalone-word matching; one expression has publisher evidence beyond an
exact dictionary-headword lookup. One vocabulary sense was corrected without
approving all Thai glosses. All 45 supporting glyphs retain their non-teaching
role and source occurrences; missing source cards/Thai glosses are not
fabricated. Exact case values and evidence snapshots remain private.

Historical primary reference links (not newly revalidated linguistic approval):
[Compound-reading reference](https://www.kanjipedia.jp/kotoba/0002118800),
[word-level reading reference](https://www.kanjipedia.jp/kanji/0002163400),
[incomplete-stem reference](https://www.kanjipedia.jp/kanji/0003907200),
[radical index (two strokes)](https://www.kanjipedia.jp/sakuin/bushu/2),
[radical index (four strokes)](https://www.kanjipedia.jp/sakuin/bushu/4),
[publisher expression sample](https://www.hituzi.co.jp/hituzibooks/img/1216meguriai1_sample_ch2.pdf),
[official legal glossary](https://www.houterasu.or.jp/site/yasasiinihongo/houritsu-saiban-kotoba.html).

## Japanese meanings and Thai translation coverage

JMdict evidence now retains applicable sense restrictions, complete English
glosses, register labels and sense notes. Dictionary membership verifies
written-form/reading pairs; it does not alone approve a Thai translation. All
210 reading answers match JMdict and all 210 meaning-answer strings agree with
their source card candidates.

Four pinned Japan Foundation Marugoto Japanese-Thai XLSX lists cover 77 unique
vocabulary pairs. Exact canonical/whitespace-normalized Thai matches: 73 source
occurrences across 61 pairs. Occurrence statuses: {'reference_exact_match': 73,
'not_covered': 147, 'sense_review_required': 20}. Card-level exact matches: 71.
Exact matches are limited field evidence, not whole-chapter approval. Different
translations are review candidates, not automatically errors: examples include
blue shades, meal versus eating, and context-sensitive family terms. Register
and context-sensitive senses remain review items. No replacement Thai gloss is
guessed. The supporting characters still lack independently approved Thai
meanings. Detailed rows, snapshot hashes, worksheets and row numbers remain
private.
[Japan Foundation reference index](https://marugoto.jpf.go.jp/teacher/resource/pre_intermediate/) -
primary lists are private verification references, not redistributed lesson
content.

## Diagrams and comparison scoring

Chapters 2 and 4 now have comparison-network views using exactly the three
supplied pairs and source labels on pages 22 and 36. Original null cores remain
null. Component endpoints have an explicit entity type and are validated against
the prepared component/Kanji records. No hub, component-position link,
historical claim or artwork file was invented. All 30 C exercises have manual,
source-grounded rubric metadata with original answer-note/page references, a
one-point maximum and no automatic credit. Twenty-three have a source memory tip
mentioning both target characters; seven have only the comparison and reference
note. Blank responses are unanswered; nonblank responses require manual review.
Even an exact source quote receives no automatic score while the rubric/content
remains unapproved.

## Remaining open requirements

| Entry                          | Remaining verification                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| thai_semantic_review_required  | Independently review uncovered/different Thai meanings, register and context, including supporting-character Thai fields. |
| mnemonic_claim_review_required | Review all source mnemonic/composition/phonetic claims; none are certified historical etymology.                          |
| diagram_visual_review_required | Review any eventual visual adaptation and reuse rights; source-pair mappings do not reconstruct the original art.         |
| comparison_rubric_required     | Teacher approval and manual grading remain necessary, especially the seven pairs without a target-specific source tip.    |

## Chapter/page reconciliation

Source chapter titles and exact educational examples are withheld from the
public report. The original full report is retained privately; numeric
reconciliation is preserved below.

| Ch. | Source pages | Cards / vocabulary | Numbered questions / answers | Diagram mapping                  |
| --- | ------------ | ------------------ | ---------------------------- | -------------------------------- |
| 1   | 11-17        | 14 / 8             | 14 / 14                      | source core graph                |
| 2   | 18-24        | 14 / 8             | 14 / 14                      | source pair network; core absent |
| 3   | 25-31        | 14 / 8             | 14 / 14                      | source core graph                |
| 4   | 32-38        | 14 / 8             | 14 / 14                      | source pair network; core absent |
| 5   | 39-45        | 14 / 8             | 14 / 14                      | source core graph                |
| 6   | 46-52        | 14 / 8             | 14 / 14                      | source core graph                |
| 7   | 53-59        | 14 / 8             | 14 / 14                      | source core graph                |
| 8   | 60-66        | 14 / 8             | 14 / 14                      | source core graph                |
| 9   | 67-73        | 14 / 8             | 14 / 14                      | source core graph                |
| 10  | 74-80        | 14 / 8             | 14 / 14                      | source core graph                |
| 11  | 81-87        | 14 / 8             | 14 / 14                      | source core graph                |
| 12  | 88-94        | 14 / 8             | 14 / 14                      | source core graph                |
| 13  | 95-101       | 14 / 8             | 14 / 14                      | source core graph                |
| 14  | 102-108      | 14 / 8             | 14 / 14                      | source core graph                |
| 15  | 109-115      | 14 / 8             | 14 / 14                      | source core graph                |
| 16  | 116-122      | 14 / 8             | 14 / 14                      | source core graph                |
| 17  | 123-129      | 14 / 8             | 14 / 14                      | source core graph                |
| 18  | 130-136      | 14 / 8             | 14 / 14                      | source core graph                |
| 19  | 137-143      | 14 / 8             | 14 / 14                      | source core graph                |
| 20  | 144-150      | 14 / 8             | 14 / 14                      | source core graph                |
| 21  | 151-157      | 14 / 8             | 14 / 14                      | source core graph                |
| 22  | 158-164      | 14 / 8             | 14 / 14                      | source core graph                |
| 23  | 165-171      | 14 / 8             | 14 / 14                      | source core graph                |
| 24  | 172-178      | 14 / 8             | 14 / 14                      | source core graph                |
| 25  | 179-185      | 14 / 8             | 14 / 14                      | source core graph                |
| 26  | 186-192      | 14 / 8             | 14 / 14                      | source core graph                |
| 27  | 193-199      | 14 / 8             | 14 / 14                      | source core graph                |
| 28  | 200-206      | 14 / 8             | 14 / 14                      | source core graph                |
| 29  | 207-213      | 14 / 8             | 14 / 14                      | source core graph                |
| 30  | 214-220      | 14 / 8             | 14 / 14                      | source core graph                |

Every original issue ID and its classification, evidence and disposition is
retained in private/json-content/audit-dispositions.json. The generated root
JSON audit also contains source-derived metadata and requires its own
publication review. See [CONTENT_PIPELINE.md](../guides/CONTENT_PIPELINE.md) and
[SEED_VALIDATION.md](SEED_VALIDATION.md).
