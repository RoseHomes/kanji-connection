"""Explicit Phase 1 offline demo. Never used as fallback for database failures."""

from fastapi import HTTPException

from .catalog import LESSONS, SAMPLES
from .schemas import LessonDetail


class SampleRepository:
    def lessons(self, q="", part=None, status=None, offset=0, limit=30):
        return [
            x
            for x in LESSONS
            if x.is_available
            and x.status == "sample"
            and (not part or x.part == part)
            and (not status or x.status == status)
            and (not q or q.casefold() in (x.title_th + " ".join(x.anchors)).casefold())
        ][offset : offset + limit]

    def lesson(self, slug):
        item = next((x for x in LESSONS if x.slug == slug and x.status == "sample"), None)
        if item is None:
            raise HTTPException(404, "ไม่พบบทเรียนที่เผยแพร่")
        return LessonDetail(
            **item.model_dump(),
            kanjis=SAMPLES,
            introduction_th="เริ่มจาก 木 แล้วสังเกตส่วนประกอบที่ซ้ำใน 林 และ 森 "
            "ภาพช่วยจำเป็นเครื่องมือฝึกจำ ไม่ใช่ประวัติทั้งหมดของอักษร",
            provenance="ตัวอย่างเขียนใหม่ ตรวจการอ่านกับ KanjiPedia; "
            "คำแปลไทยรอตรวจบรรณาธิการ ไม่ใช่บทที่ 2 ฉบับเต็มจากหนังสือ",
        )

    def kanjis(self, q="", offset=0, limit=30):
        return [
            x
            for x in SAMPLES
            if q.casefold()
            in " ".join(
                [x.character, x.meaning_th, *x.onyomi, *x.kunyomi, x.romaji, x.component]
            ).casefold()
        ][offset : offset + limit]

    def kanji(self, character):
        item = next((x for x in SAMPLES if x.character == character), None)
        if item is None:
            raise HTTPException(404, "ไม่พบคันจิในชุดตัวอย่าง")
        return item

    def compare(self, characters):
        return [self.kanji(c) for c in characters]

    def relations(self, character):
        self.kanji(character)
        return {
            "character": character,
            "type": "same_component",
            "component": "木",
            "related": [x.character for x in SAMPLES if x.character != character],
        }

    def vocabulary(self, character, offset=0, limit=30):
        self.kanji(character)
        return []
