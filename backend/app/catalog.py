"""Generic demo metadata, independent of the private book curriculum.

Database-backed deployments read lesson titles from PostgreSQL. These numbered
demo slots preserve sample navigation and are not a transcription of the book.
"""

from .schemas import Kanji, Lesson

SAMPLES = [
    Kanji(
        character="木",
        meaning_th="ต้นไม้; ไม้",
        onyomi=["ボク", "モク"],
        kunyomi=["き", "こ"],
        romaji="ki",
        strokes=4,
        component="木",
        note_th="ภาพช่วยจำ: มองเส้นกลางเป็นลำต้น และเส้นด้านข้างเป็นกิ่งไม้",
        source_url="https://www.kanjipedia.jp/kanji/0006470400",
    ),
    Kanji(
        character="林",
        meaning_th="ป่า; หมู่ต้นไม้",
        onyomi=["リン"],
        kunyomi=["はやし"],
        romaji="hayashi",
        strokes=8,
        component="木",
        note_th="ภาพช่วยจำ: 木 สองตัววางข้างกัน ชวนให้นึกถึงต้นไม้ที่ขึ้นรวมกัน",
        source_url="https://www.kanjipedia.jp/kanji/0007198600",
    ),
    Kanji(
        character="森",
        meaning_th="ป่า; ป่าไม้",
        onyomi=["シン"],
        kunyomi=["もり"],
        romaji="mori",
        strokes=12,
        component="木",
        note_th="ภาพช่วยจำ: 木 สามตัว ชวนให้นึกถึงต้นไม้ที่ขึ้นหนาแน่น",
        source_url="https://www.kanjipedia.jp/kanji/0003641700",
    ),
]

LESSONS = [
    Lesson(
        id=i,
        chapter=i,
        is_available=i == 2,
        slug=f"chapter-{i:02}",
        part=(i - 1) // 5 + 1,
        title_th="ห้องทดลองคันจิ: ต้นไม้" if i == 2 else f"แบบฝึกสาธิต {i:02}",
        summary_th="พื้นที่สาธิตการใช้งานแอป ไม่ใช่เนื้อหาบทเรียนจากหนังสือ",
        anchors=[k.character for k in SAMPLES] if i == 2 else [],
        status="sample" if i == 2 else "needs_review",
        available_count=3 if i == 2 else 0,
    )
    for i in range(1, 31)
]
