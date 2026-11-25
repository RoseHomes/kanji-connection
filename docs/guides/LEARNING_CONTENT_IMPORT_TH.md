# คู่มือนำเข้าเนื้อหาตามหมวดและ JLPT

ใช้ `scripts/import_learning_content.py` กับ schema revision `0003` สำหรับงานเตรียมเนื้อหาใหม่ `backend/app/expansion_import.py` ตรวจ schema ของแผนนำเข้าและใช้ตัวเขียนแบบ insert-only ร่วมกับตัวนำเข้าหนังสือ คำสั่ง apply จำกัดให้รันบน PostgreSQL ที่ `127.0.0.1` ชื่อ `kanji_test` หรือ `kanji_expansion_dev` โดยอ่าน DSN จาก `EXPANSION_TEST_DATABASE_URL` เท่านั้น

โมเดลแผนรองรับระดับ 1–5 ส่วนตัวอ่าน OpenJLPT ในรอบนี้เตรียมเฉพาะ N5 แผนที่มีเฉพาะหมวดสามารถใช้ `reference: null` และไม่มี `assignments`

## 1. เตรียมและตรวจสอบข้อมูลอ้างอิง

รันจาก root โครงการใน PowerShell

```powershell
$python = '.\.venv\Scripts\python.exe'
$importer = 'scripts/import_learning_content.py'
& $python $importer fetch
& $python $importer capture-current
& $python $importer prepare
```

- `fetch` ตรวจ SHA-256 ของไฟล์ CSV, JSON, `NOTICE.md` และ `LICENSE` ที่ commit `0d1d3410bec90bd4098a7c72de820543cb4f707c` และใช้ไฟล์เดิมเมื่อตรง hash [OpenJLPT snapshot](https://github.com/evanclan/OpenJLPT/tree/0d1d3410bec90bd4098a7c72de820543cb4f707c)
- `capture-current` ใช้การเชื่อมต่ออ่านของ runtime ใน transaction แบบ `REPEATABLE READ, READ ONLY` เก็บเฉพาะตารางเนื้อหา ตรวจนับจาก snapshot โดยไม่แตะตารางบัญชี ใช้ `--output private/<โฟลเดอร์ใหม่>` ก่อนชื่อคำสั่งเมื่อเปลี่ยน baseline และเก็บไฟล์ baseline ไว้ในพื้นที่ private
- `prepare` ต้องมี `private/dictionaries/JMdict_e.gz` และ sidecar `.source.json` ที่ผ่าน checksum ตัวตรวจเทียบ `re_restr`, `re_nokanji`, `stagk` และ `stagr` รุ่นพจนานุกรมและ hash ถูกบันทึกใน release manifest หากต้องระบุไฟล์อื่นให้ส่ง `--jmdict <path>` ก่อนชื่อคำสั่ง การทบทวนรูปเขียนและคำอ่านใช้แหล่งที่มาของแต่ละคู่ [เงื่อนไข EDRDG](https://www.edrdg.org/edrdg/licence.html)

## 2. อ่านผลและตัดสินใจทีละรายการ

| ไฟล์ใน `private/jlpt-n5-import/` | ใช้ตรวจอะไร |
| --- | --- |
| `reference-inventory.json` | ทุกรายการใน reference พร้อม upstream key, คำอ่าน, รูปแปร, senses, ตัวชี้ไปยังแหล่งประโยค และลำดับเดิม |
| `canonical-mappings.json` | ผลเทียบ canonical, แถวที่ตรง, แถวที่อาจตรงแบบรูปแปร, รูปเขียนเดียวแต่ต่างคำอ่าน, provenance, fingerprint และข้อที่ต้องตรวจ |
| `new-and-unresolved.json` | คิวเพิ่มระเบียนหรือพิจารณารูปแปร |
| `validation-and-conflicts.json` และ `editorial-review.csv` | ผลรวม เหตุที่ติดค้าง และช่องบันทึกผลตรวจ หาก CSV มีผลตรวจในคอลัมน์บรรณาธิการ การรันซ้ำจะเขียน `editorial-review.regenerated.csv` ให้เทียบก่อนรวม |
| `unit-proposals.json` และ `category-proposals.json` | ข้อเสนอหน่วยและหมวดจากการเลือกด้วยมือ คิวที่ยังไม่ได้จัดหมวด และ prerequisites เชิงบรรณาธิการ |
| `audio-coverage.json` | ผลค้นหา index เดิมด้วยชนิด ข้อความ คำอ่าน และขอบเขตการใช้ พร้อมประมาณพื้นที่จากขนาด MP3 เดิม |
| `import-manifest.json` และ `approval-template.json` | แผนร่างและแบบฟอร์มอนุมัติ แถวที่มีความหมายไทยหรือใช้เสียงได้ในคลังเดิมยังต้องผ่านการตรวจสำหรับบริบทของเส้นทางใหม่ |

ตรวจการสะกด NFC และคีย์ `(written_form, reading)` โดย normalize คาตาคานะเป็นฮิรางานะเฉพาะด้านคำอ่าน ให้บรรณาธิการเลือกความหมายและตรวจคำพ้องเสียง คำอ่านอื่น และรูปเขียนตามบริบท เมื่อสองรายการอ้างอิงชี้ไป lexical identity เดียวกัน ให้บันทึกคำตัดสินและเลือก assignment ที่จะใช้กับ canonical target หนึ่งรายการต่อ release/level ตัวชี้อ้างอิงทั้งสองยังอยู่ใน inventory ไม่มีการนับซ้ำเป็นเนื้อหาใหม่

บันทึกเซนส์ที่เลือก แหล่งคำอ่าน ความหมายไทย ประโยค และสิทธิ์ก่อนเพิ่ม `new_content` แหล่งประโยคจาก Tatoeba ต้องตรวจเครดิตของประโยคและคำแปลตาม ID และหลักฐานจริง รวมถึงสิทธิ์ก่อนคัดข้อความ ประโยคจากหนังสือเดิมทั้งห้ารายการให้ตรวจสิทธิ์ใช้ซ้ำในเส้นทางใหม่และความเกี่ยวข้องกับหน่วยก่อนเพิ่ม ระดับ JLPT ในไฟล์เป็นระบบอ้างอิงเพื่อเตรียมสอบ [OpenJLPT NOTICE](https://github.com/evanclan/OpenJLPT/blob/0d1d3410bec90bd4098a7c72de820543cb4f707c/NOTICE.md) · [JLPT FAQ](https://jlpt.jp/sp/e/faq/index.html)

## 3. ซ้อมแผนและบันทึกการอนุมัติ

คัดลอก `import-manifest.json` เป็น `reviewed-manifest.json` แล้วแก้ในสำเนา ให้แผนเหลือเฉพาะระเบียน การจัดระดับ หน่วย และ membership ที่บรรณาธิการอนุมัติ ใช้ `reuse` พร้อม canonical fingerprint สำหรับระเบียนเดิม ใช้ `new_content` พร้อมข้อมูลและเครดิตที่ตรวจแล้วสำหรับระเบียนใหม่ เลือกตำแหน่งหน่วยที่ว่างในเส้นทางเดิม และจัด membership ทุกตัวไว้ในหน่วย `needs_review` แม้หมวดแม่จะเปิดอยู่แล้ว

ตั้ง `EXPANSION_TEST_DATABASE_URL` ให้ชี้ PostgreSQL สำหรับทดสอบที่ว่างและฟังเฉพาะ loopback แล้วรัน

```powershell
$folder = 'private/jlpt-n5-import'
$plan = "$folder/reviewed-manifest.json"
& $python $importer dry-run --manifest $plan
$hash = (Get-Content "$folder/dry-run-results.json" -Raw | ConvertFrom-Json).plan_sha256
```

`dry-run` สร้าง schema ใน transaction บนฐานทดสอบว่าง ใส่ snapshot ต้นฉบับ ซ้อมแผนสองครั้ง เปรียบเทียบ public paths และข้อมูลเดิม แล้ว rollback ทั้ง DDL และข้อมูล ตรวจว่าตารางใน `public` ว่างอีกครั้ง `dry-run-<sha>.json` เป็นหลักฐานของแต่ละแผน ส่วน `dry-run-results.json` ชี้ผลซ้อมล่าสุด

ผู้อนุมัติที่ได้รับมอบหมายต้องจัดทำ `approval.json` แยกจาก template โดยระบุ `plan_sha256` ให้ตรงกับผลซ้อม, `reviewer`, `decision_reference` ที่อ้างกลับไปใบตรวจเนื้อหา/สิทธิ์ได้ และ `approved: true` ระบุ hash เดียวกันอย่างชัดเจนใน CLI หากแก้แผนต้องซ้อมและขออนุมัติใหม่

```powershell
& $python $importer seal --manifest $plan --approval "$folder/approval.json" --approve-sha256 $hash
```

`seal` ตรวจหลักฐานและเขียนไฟล์ manifest/decision ลงพื้นที่ private ส่วน `apply` เป็นคำสั่งเดียวที่ commit และต้องมีการอนุมัติอย่างชัดเจนสำหรับการนำเข้าจริง ตั้ง DSN ใหม่ให้เป็นของฐาน staging ภายในเครื่อง แล้วเลือกใส่ `--bootstrap-empty` เฉพาะครั้งแรกบนฐานว่างที่ต้องสร้างสำเนาคลังจาก snapshot

```powershell
& $python $importer apply `
  --manifest "$folder/approved-$hash.manifest.json" `
  --approval "$folder/approved-$hash.decision.json" `
  --approve-sha256 $hash --bootstrap-empty
```

การรันซ้ำกับ staging revision `0003` ที่เตรียมไว้แล้วให้ตัด `--bootstrap-empty` ออก แผนใช้ natural keys, foreign keys, advisory lock และ transaction เดียว ข้อมูลที่มีอยู่และตรงกันจะถูกข้าม หากค่าขัดกัน งานทั้งก้อน rollback ให้ตรวจ conflict และซ้อมแผนใหม่ก่อนดำเนินการต่อ

## 4. เกณฑ์ก่อนเผยแพร่ในเฟสถัดไป

1. ปิดข้อค้างเรื่องความหมายไทย เซนส์ รูปแปร คำอ่าน ประโยค สิทธิ์ แหล่งอ้างอิง และการตรวจเสียงตามขอบเขต release
2. ตรวจหน่วยที่จะเปิดจริง สรุปตัวหาร OpenJLPT แยกจากจำนวนรายการพร้อมเรียน และทดสอบ Guided Learning, Full Lesson, หมวด, การกรอง JLPT, ข้อมูล private และ 30 บทเดิมบน staging
3. ขออนุมัติการเผยแพร่แยกต่างหาก รวมถึงการใช้ revision `0003` บน production หากยังอยู่ที่ `0002` เตรียม backup และแผนย้อนสถานะก่อนใช้ deployment workflow ที่ได้รับอนุญาต
4. ใช้ publication transaction ที่ผ่าน review กับชุดแถวที่อนุมัติเท่านั้น ตรวจ mapping กับ release/level และสิทธิ์ของ target ก่อนสลับ visibility แล้วตรวจ public API หลังเผยแพร่ คงแถวบทเดิมและประวัติผู้เรียนไว้ Pipeline ในคู่มือนี้จบที่ staging แบบ private
