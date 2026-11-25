"""Private, insert-only plans for the revision 0003 learning catalog."""

import re
import unicodedata
from collections import defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from .book_bundle import ref
from .book_import import MODELS, insert_rows
from .content_revision import digest
from .editorial_sync import normalized

Kind = Literal["kanji", "vocabulary", "sentence"]
SHA = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)]
Thai = Annotated[str, Field(pattern=r"[ก-๛]", max_length=1000)]
Kana = re.compile(r"(?=[ぁ-ゖァ-ヺー・.\-]*[ぁ-ゖァ-ヺ])[ぁ-ゖァ-ヺー・.\-]+")
SENTENCE_PUNCTUATION = str.maketrans("", "", "、。！？!? ,．.　「」『』（）()")
Han = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]")
JP = re.compile(r"[ぁ-ゖァ-ヺ\u3400-\u9fff\U00020000-\U000323af]")
TABLE = {"kanji": "kanjis", "vocabulary": "vocabularies", "sentence": "example_sentences"}
TARGET_FK = {"kanji": "kanji_id", "vocabulary": "vocabulary_id", "sentence": "sentence_id"}
VISIBILITY = {"status": "needs_review", "access_tier": "private"}


def nfc(value):
    return unicodedata.normalize("NFC", value.strip())


def kana(value):
    return "".join(chr(ord(c) - 96) if "ァ" <= c <= "ヶ" else c for c in nfc(value))


def pair(kind, text, reading=""):
    pronunciation = kana(reading)
    if kind == "sentence":
        pronunciation = pronunciation.translate(SENTENCE_PUNCTUATION)
    return kind, nfc(text), pronunciation


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credit(Model):
    source_url: Annotated[str, Field(pattern=r"^https?://[^\s]+$", max_length=500)]
    license: Literal["CC BY-SA 4.0", "CC BY 4.0", "CC BY 2.0 FR", "CC0 1.0", "owner-authorized"]
    attribution: Annotated[str, Field(min_length=1, max_length=2000)]
    evidence: Annotated[str, Field(min_length=1, max_length=1000)]


class ReferenceRelease(Credit):
    source_key: Slug
    version: Annotated[str, Field(min_length=1, max_length=120)]
    manifest: dict
    manifest_sha256: SHA

    @model_validator(mode="after")
    def verify_digest(self):
        if digest(self.manifest) != self.manifest_sha256:
            raise ValueError("Reference release manifest checksum differs")
        return self


class Target(Model):
    kind: Kind
    text: Annotated[str, Field(min_length=1, max_length=500)]
    reading: Annotated[str, Field(max_length=400)] = ""

    @model_validator(mode="after")
    def validate_japanese(self):
        if (
            self.text != nfc(self.text)
            or not JP.search(self.text)
            or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in self.text)
        ):
            raise ValueError("Japanese text must be NFC and contain Japanese characters")
        if self.kind == "kanji" and (not Han.fullmatch(self.text) or self.reading):
            raise ValueError("Kanji identity is exactly one Han glyph")
        if self.kind == "vocabulary" and (
            len(self.text) > 150 or not self.reading or len(self.reading) > 200
        ):
            raise ValueError("Vocabulary requires a written form and reading within column bounds")
        if self.reading and (
            self.reading != nfc(self.reading) or not Kana.fullmatch(self.identity()[2])
        ):
            raise ValueError("Reading must be NFC kana")
        return self

    def identity(self):
        return pair(self.kind, self.text, self.reading)

    def key(self):
        if self.kind == "kanji":
            return {"character": self.text}
        return {
            "written_form" if self.kind == "vocabulary" else "text_ja": self.text,
            "reading": self.reading,
        }

    def foreign_key(self):
        return ref(TABLE[self.kind], self.key())


class NewContent(Model):
    target: Target
    meaning_th: Thai
    credit: Credit
    usage_notes: Annotated[str, Field(max_length=2000)] = ""
    dictionary_id: Annotated[str, Field(pattern=r"^[0-9]{6,9}$")] | None = None
    readings: dict[Literal["on", "kun", "other"], list[str]] = Field(default_factory=dict)
    strokes: int | None = Field(default=None, ge=1, le=99)

    @model_validator(mode="after")
    def validate_details(self):
        if self.target.kind == "kanji":
            if self.dictionary_id is not None or not any(self.readings.values()):
                raise ValueError("New kanji requires attested readings grouped by kind")
            for values in self.readings.values():
                if any(v != nfc(v) or not Kana.fullmatch(v) for v in values) or len(
                    set(map(kana, values))
                ) != len(values):
                    raise ValueError("Invalid or duplicate kanji reading")
            if len(self.meaning_th) > 500:
                raise ValueError("Kanji translation exceeds its column length")
        elif (
            self.readings
            or self.strokes is not None
            or (self.target.kind == "sentence" and self.dictionary_id)
        ):
            raise ValueError("Misplaced kanji or dictionary metadata")
        return self


class Reuse(Model):
    target: Target
    row_sha256: SHA


class Assignment(Model):
    reference_key: Annotated[str, Field(min_length=1, max_length=200)]
    target: Target
    method: Literal["exact", "reviewed_variant"] = "exact"
    evidence: Annotated[str, Field(max_length=1000)] = ""


class Placement(Model):
    target: Target
    required: bool = True
    context_note_th: Annotated[str, Field(max_length=2000)] = ""


class Unit(Model):
    key: Slug
    title_th: Annotated[Thai, Field(max_length=300)]
    intro_th: Annotated[str, Field(max_length=4000)] = ""
    position: int = Field(ge=0)
    items: Annotated[list[Placement], Field(min_length=1)]


class PathPlan(Model):
    kind: Literal["category", "jlpt"]
    slug: Slug
    title_th: Annotated[str, Field(min_length=1, max_length=300)]
    position: int = Field(ge=0)
    level: int | None = Field(default=None, ge=1, le=5)
    units: Annotated[list[Unit], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_path(self):
        if (self.level is not None) != (self.kind == "jlpt"):
            raise ValueError("Only JLPT paths carry a level")
        unique((u.key for u in self.units), "unit key")
        unique((u.position for u in self.units), "unit order")
        unique((i.target.identity() for u in self.units for i in u.items), "path membership")
        return self


def unique(values, label):
    values = list(values)
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


class ImportPlan(Model):
    schema_version: Literal[1] = 1
    catalog_sha256: SHA
    reference: ReferenceRelease | None = None
    new_content: list[NewContent] = Field(default_factory=list)
    reuse: list[Reuse] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
    paths: list[PathPlan] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self):
        targets = [x.target for x in self.new_content + self.reuse]
        unique((t.identity() for t in targets), "canonical target")
        unique((a.reference_key for a in self.assignments), "reference key")
        unique(((p.kind, p.slug) for p in self.paths), "path")
        unique((p.level for p in self.paths if p.level is not None), "JLPT path level")
        if self.reference is None and (
            self.assignments or any(p.kind == "jlpt" for p in self.paths)
        ):
            raise ValueError("JLPT data requires a pinned reference")
        declared = {tuple(t.key().values()) + (t.kind,) for t in targets}
        used = [a.target for a in self.assignments] + [
            i.target for p in self.paths for u in p.units for i in u.items
        ]
        if any(tuple(t.key().values()) + (t.kind,) not in declared for t in used):
            raise ValueError("Assignment or membership references an undeclared target")
        return self


def row_target(kind, row):
    return pair(
        kind,
        row.get("character") or row.get("written_form") or row["text_ja"],
        row.get("reading", ""),
    )


def index_catalog(tables):
    by_identity = defaultdict(list)
    for kind, table in TABLE.items():
        for row in tables.get(table, []):
            by_identity[row_target(kind, row)].append(row)
    return by_identity


def _record_values(record, reference_evidence):
    target = record.target
    provenance = record.credit.model_dump()
    if reference_evidence:
        provenance["reference_keys"] = sorted(reference_evidence)
    if record.dictionary_id:
        provenance["jmdict_id"] = record.dictionary_id
    if target.kind == "kanji":
        return {
            "meaning_th": record.meaning_th,
            "readings": record.readings,
            "review_status": "needs_review",
            "source": provenance,
            "note_th": record.usage_notes,
            "strokes": record.strokes,
            "access_tier": "private",
        }
    return {
        "meaning_th": record.meaning_th,
        "provenance": provenance,
        **VISIBILITY,
        "usage_notes" if target.kind == "vocabulary" else "usage_notes_th": record.usage_notes,
    }


def apply_plan(session, plan, reference_rows=(), *, trusted_release=None):
    """Validate then stage one atomic batch. Caller owns the outer commit/rollback."""
    reference_rows = list(reference_rows)
    if plan.reference != trusted_release or (
        plan.reference and digest(reference_rows) != plan.reference.manifest.get("inventory_sha256")
    ):
        raise ValueError("Plan reference does not match the independently verified inventory")
    refs = {row["key"]: row for row in reference_rows}
    by_identity = index_catalog(
        {
            table: [dict(r) for r in session.execute(select(MODELS[table].__table__)).mappings()]
            for table in TABLE.values()
        }
    )
    existing_words = [
        r for identity, rows in by_identity.items() if identity[0] == "vocabulary" for r in rows
    ]
    operations = []

    def add(table, key, **values):
        for name, value in {**key, **values}.items():
            maximum = getattr(MODELS[table].__table__.c[name].type, "length", None)
            if maximum and isinstance(value, str) and len(value) > maximum:
                raise ValueError(f"Value exceeds {table}.{name} length")
        operations.append({"table": table, "key": key, "values": values})

    assigned = defaultdict(set)
    assignments_by_target = defaultdict(list)
    for a in plan.assignments:
        row = refs.get(a.reference_key)
        identity = a.target.identity()
        if not row or a.target.kind != row["kind"]:
            raise ValueError("Unknown or incompatible reference assignment")
        exact = identity == pair(row["kind"], row["text"], row.get("reading", ""))
        alternatives = {
            pair(row["kind"], alias["text"], alias["reading"]) for alias in row.get("aliases", [])
        }
        if (a.method == "exact" and not exact) or (
            a.method == "reviewed_variant" and (not a.evidence or identity not in alternatives)
        ):
            raise ValueError("Assignment has no verified written form and reading")
        level = row["level"]
        if identity in assigned[level]:
            raise ValueError("Two reference records map to one target at the same level")
        assigned[level].add(identity)
        assignments_by_target[identity].append(row["key"])
    for entry in plan.reuse:
        rows = by_identity[entry.target.identity()]
        if (
            len(rows) != 1
            or not all(rows[0][k] == v for k, v in entry.target.key().items())
            or digest(normalized(rows[0])) != entry.row_sha256
        ):
            raise ValueError(
                f"Reused canonical record is missing, changed, or ambiguous: {entry.target.key()}"
            )
    new_targets = {entry.target.identity(): entry.target for entry in plan.new_content}
    for entry in plan.new_content:
        t = entry.target
        identity = t.identity()
        rows = by_identity.get(identity, [])
        if len(rows) > 1 or (rows and not all(rows[0][k] == v for k, v in t.key().items())):
            raise ValueError(f"Normalized duplicate: {t.key()}")
        if t.kind == "sentence" and any(
            k[0] == "sentence"
            and k[1] == identity[1]
            and k != identity
            and (not k[2] or not identity[2])
            for k in by_identity
        ):
            raise ValueError("Sentence is already present with an unresolved reading")
        evidence = assignments_by_target[identity]
        known_aliases = {
            pair(t.kind, alias["text"], alias["reading"])
            for k in evidence
            for alias in refs[k].get("aliases", [])
        }
        if (known_aliases - {identity}) & (by_identity.keys() | new_targets.keys()):
            raise ValueError(f"Existing dictionary alias requires reconciliation: {t.key()}")
        dictionary_id = entry.dictionary_id
        if t.kind == "kanji" and evidence:
            for kind, values in entry.readings.items():
                attested = {
                    kana(v) for k in evidence for v in refs[k].get("readings", {}).get(kind, [])
                }
                if not set(map(kana, values)) <= attested:
                    raise ValueError(
                        "New kanji readings must be attested in the reference inventory"
                    )
        if t.kind == "vocabulary" and evidence:
            ids = {refs[k].get("dictionary_id") for k in evidence} - {None, ""}
            if ids and ids != {dictionary_id}:
                raise ValueError("New vocabulary must carry its verified dictionary identity")
        if dictionary_id and any(
            str(w["provenance"].get("jmdict_id")) == dictionary_id
            and row_target("vocabulary", w) != identity
            for w in existing_words
        ):
            raise ValueError("Existing JMdict identity requires editorial reconciliation")
        add(TABLE[t.kind], t.key(), **_record_values(entry, evidence))
        if t.kind == "vocabulary":
            for position, character in enumerate(t.text):
                if not Han.fullmatch(character):
                    continue
                glyph = pair("kanji", character)
                matched = by_identity.get(glyph, [])
                if len(matched) > 1:
                    raise ValueError("Vocabulary contains an ambiguous canonical glyph")
                if matched or glyph in new_targets:
                    glyph_key = {"character": matched[0]["character"] if matched else character}
                    add(
                        "vocabulary_kanjis",
                        {"vocabulary_id": t.foreign_key(), "position": position},
                        kanji_id=ref("kanjis", glyph_key),
                    )
        for kind, readings in entry.readings.items():
            for position, reading in enumerate(readings):
                add(
                    "kanji_readings",
                    {"kanji_id": t.foreign_key(), "kind": kind, "reading": reading},
                    position=position,
                    notes="",
                )
    unique((e.dictionary_id for e in plan.new_content if e.dictionary_id), "new JMdict identity")
    if plan.reference:
        release = plan.reference
        release_key = {"source_key": release.source_key, "version": release.version}
        release_fk = ref("jlpt_reference_releases", release_key)
        add(
            "jlpt_reference_releases",
            release_key,
            **release.model_dump(exclude={"source_key", "version", "evidence"}),
        )
        for a in plan.assignments:
            row = refs[a.reference_key]
            add(
                "jlpt_assignments",
                {"release_id": release_fk, "reference_key": a.reference_key},
                level=row["level"],
                **{TARGET_FK[a.target.kind]: a.target.foreign_key()},
                match_provenance={
                    "method": a.method,
                    "evidence": a.evidence,
                    "reference_order": row["order"],
                    "reference_file": row["file"],
                    "jmdict_id": row.get("dictionary_id"),
                },
            )
    for p in plan.paths:
        path_key = {"kind": p.kind, "slug": p.slug}
        path_model = MODELS["learning_paths"]
        current = session.scalar(select(path_model).filter_by(**path_key))
        path_fk = ref("learning_paths", path_key)
        release_values = (
            {"jlpt_level": p.level, "jlpt_release_id": release_fk} if p.kind == "jlpt" else {}
        )
        if current is None:
            add(
                "learning_paths",
                path_key,
                title_th=p.title_th,
                sort_order=p.position,
                **release_values,
                **VISIBILITY,
            )
        elif p.kind == "jlpt":
            release_model = MODELS["jlpt_reference_releases"]
            current_release = session.get(release_model, current.jlpt_release_id)
            if (
                current.jlpt_level != p.level
                or not current_release
                or any(getattr(current_release, k) != v for k, v in release_key.items())
            ):
                raise ValueError("Existing JLPT path pins a different level or release")
        if current is not None:
            unit_model = MODELS["learning_units"]
            planned = {u.position: u.key for u in p.units}
            for unit in session.scalars(select(unit_model).where(unit_model.path_id == current.id)):
                if unit.sort_order in planned and planned[unit.sort_order] != unit.unit_key:
                    raise ValueError(
                        "Unit order collides with an existing unit in the learning path"
                    )
        for unit in p.units:
            unit_key = {"path_id": path_fk, "unit_key": unit.key}
            add(
                "learning_units",
                unit_key,
                title_th=unit.title_th,
                intro_th=unit.intro_th,
                sort_order=unit.position,
                status="needs_review",
            )
            for position, item in enumerate(unit.items):
                t = item.target
                if (
                    p.kind == "jlpt"
                    and t.kind != "sentence"
                    and t.identity() not in assigned[p.level]
                ):
                    raise ValueError(
                        "JLPT member needs an assignment at the path level and release"
                    )
                add(
                    "learning_path_items",
                    {"path_id": path_fk, TARGET_FK[t.kind]: t.foreign_key()},
                    unit_id=ref("learning_units", unit_key),
                    sort_order=position,
                    required=item.required,
                    context_note_th=item.context_note_th,
                )
    with session.begin_nested():
        result = insert_rows(session, operations)
        if result["conflicts"]:
            keys = [
                {"table": c["table"], "key": c["key"], "fields": c["fields"]}
                for c in result["conflicts"]
            ]
            raise ValueError(f"Insert-only plan conflicts with existing rows: {keys}")
    return result
