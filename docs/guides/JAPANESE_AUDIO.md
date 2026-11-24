# สร้างและตรวจเสียงภาษาญี่ปุ่นบน Windows

ใช้ VOICEVOX ที่ติดตั้งในเครื่อง เลือกเสียง **四国めたん (Shikoku Metan) — ノーマル** ซึ่ง Engine `0.26.2` ที่ `http://127.0.0.1:50021` รายงานเป็น style ID `2` สคริปต์ตรวจชื่อ สไตล์ และ UUID จาก Engine ทุกครั้งก่อนสร้างเสียง ใช้ Python 3.13 ของโครงการ ตัวสร้าง WAV ใช้ไลบรารีมาตรฐานของ Python และส่งข้อความผ่าน HTTP ภายในเครื่อง [เอกสาร VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine)

## เปิด Engine และรันชุดตัวอย่างหรือสร้างต่อ

เปิดแอป VOICEVOX ค้างไว้ แล้วเปิด PowerShell ที่โฟลเดอร์รากของ `kanji-connection`

```powershell
python -X utf8 scripts/generate_voicevox_audio.py probe
python -X utf8 scripts/generate_voicevox_audio.py sample
```

ถ้า `python` ใช้งานไม่ได้ ให้ใช้ `.\.venv\Scripts\python.exe` ของโครงการแทน หาก `probe` เชื่อมต่อไม่ได้ ให้เปิด `http://127.0.0.1:50021/docs` ในเบราว์เซอร์เพื่อตรวจว่า Engine เริ่มทำงานแล้ว ถ้าตั้งพอร์ตอื่น ให้ระบุ `--engine http://127.0.0.1:พอร์ต` โดยแทน `พอร์ต` ด้วยหมายเลขจริง

ไฟล์อยู่ใน `private/audio-voicevox/wav/` คำสั่ง `sample` เลือกเฉพาะรายการตัวอย่างใน manifest เมื่อรันซ้ำ สคริปต์จะตรวจความสมบูรณ์ของไฟล์เดิมและรายงาน `skipped_existing` หากไฟล์เดิมเสียหาย ระบบจะแจ้ง `failed` พร้อมรายละเอียดในรายงาน ให้ย้ายไฟล์เสียไปเก็บต่างหากก่อนรันซ้ำ การเชื่อมต่อขัดข้องชั่วคราวจะลองใหม่สูงสุดสามครั้งต่อคำขอ รายงาน JSONL แยกตามรอบพร้อมสถานะของแต่ละไฟล์

สร้างหรือรันต่อจาก manifest ฉบับผลิตจริงด้วยคำสั่งนี้ รายงานใหม่อยู่ข้าง manifest และมีชื่อแตกต่างกันตามรอบ

```powershell
python -X utf8 scripts/generate_voicevox_audio.py all-ready --manifest private/audio-voicevox/production-manifest.json
```

`production-manifest.json` เก็บผลตรวจคำอ่าน และเก็บค่าที่ส่งให้ Engine แยกจากคำอ่านในบทเรียนในกรณีที่ต้องใช้ตัวเขียนเต็มเพื่อให้ Engine อ่านถูกต้อง สคริปต์ตรวจโมระก่อนสร้าง WAV เสมอ

## เปิดรายการและฟังเสียง

```powershell
$audioManifest = Get-Content private/audio-voicevox/manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json
$audioManifest.sample | Format-Table type, text, verified_reading, path -AutoSize
# เปิดคลิปตัวอย่างลำดับแรก เปลี่ยนเลขในวงเล็บเพื่อเลือกคลิปอื่น
Invoke-Item (Join-Path private/audio-voicevox $audioManifest.sample[0].path)
```

`sample-run.jsonl` มีชื่อไฟล์ ข้อความ คำอ่าน ลำดับโมระที่ Engine คืนมา และ SHA-256 ของตัวอย่างทั้ง 20 ไฟล์ ชุดนี้ประกอบด้วย音読み 4 คลิป 訓読み 3 คลิป คำศัพท์ 7 คลิป วลี 1 คลิป และประโยคครบทั้ง 5 รายการในบทเรียนที่ใช้เป็นแหล่งข้อมูล

1. เปิด `production-manifest.review.csv` ด้วย Excel หรือโปรแกรมที่อ่าน UTF-8 ได้ ใช้ `content_id` ค้นใน `production-manifest.review.json` เพื่อดูที่มาระดับบทเรียน หลักฐาน และเหตุผลของแต่ละกรณี `contextual_audio` ใช้คลิปคำเต็มเฉพาะบทที่ระบุ `reference_only` เป็นคำอ่านแบบมีบริบทประกอบในพจนานุกรมและเก็บไว้ให้ตรวจสอบ ส่วน `needs_manual_review` ต้องยืนยันคำอ่านในบริบทก่อนนำไปสร้างเสียง
2. ให้ผู้ตรวจที่ชำนาญภาษาญี่ปุ่นฟังคลิปเทียบกับข้อความและบริบท ตรวจเสียงสั้น–ยาว เสียงกัก `っ` เสียงควบ จังหวะ การลงเสียงสูง–ต่ำ และความเป็นธรรมชาติของประโยค สำหรับไฟล์ที่ใช้ร่วมกัน ให้ตรวจว่าการลงเสียงเหมาะกับทุกบริบทที่ต้องการใช้
3. คัดลอก `release/pronunciation-review.csv` ไปเป็นไฟล์บันทึกของผู้ตรวจ ระบุผู้ตรวจ วันที่ ผลตรวจ และหมายเหตุ โดยอ้างถึง `content_id`, `audio_id` และ SHA-256 ของ MP3 ทดสอบไฟล์ MP3 ที่จะใช้จริงในเว็บ สถานะ `ready_for_preview` หมายถึงมีหลักฐานพอสำหรับสร้างเสียง รายงานการสร้างจะให้สถานะการฟังเป็น `pending` เสมอ
4. หาก Engine อ่านคลาดเคลื่อน ระบบจะแจ้ง `failed` ก่อนสร้าง WAV ทบทวนคำอ่านและการแบ่งวลีใน VOICEVOX ก่อนสร้างไฟล์ฉบับแก้ไข แล้วตรวจฟังไฟล์และบันทึก SHA-256 ใหม่

## สร้าง manifest ซ้ำ

ตัวสร้างอ่านฐานข้อมูล SQLite ในเครื่องแบบ read-only เปรียบเทียบ SHA-256 กับใบยืนยันก่อนเผยแพร่ จำลองการเปลี่ยนสถานะในหน่วยความจำ และเปรียบเทียบกับ SHA-256 หลังเผยแพร่ ใช้ snapshot ใน `private/editorial-preview/snapshots/` ใบยืนยันใน `private/publication-release/` ข้อมูลแก้ไขใน `private/editorial-revisions/` และพจนานุกรม KANJIDIC2 กับ JMdict ที่โครงการเก็บไว้ใน `private/dictionaries/`

ต้องติดตั้ง dependency ฝั่ง backend ใน virtual environment สำหรับขั้นนี้ เลือกโฟลเดอร์ผลลัพธ์ใหม่ใต้ `private/` เพื่อเก็บชุดเดิมไว้

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_japanese_audio_manifest.py --output private/audio-voicevox-rebuild
python -X utf8 scripts/generate_voicevox_audio.py sample --manifest private/audio-voicevox-rebuild/manifest.json
```

`manifest.json` เก็บข้อความต้นฉบับ คำอ่านที่ตรวจจากแหล่งอ้างอิง ค่าที่ส่งให้ Engine พาธ WAV และแหล่งที่ใช้ในแต่ละบท คำอ่านที่มีจุดกำกับ okurigana เก็บรูปเดิมในแหล่งอ้างอิงและรวมเป็นเสียงเดียวเมื่อออกเสียงตรงกัน รายการคำศัพท์และคำอ่านแยกเดี่ยวส่ง kana เพื่อคงคำอ่านที่บทเลือก วลีและประโยคส่งข้อความเดิมเพื่อให้ Engine วิเคราะห์บริบทและเปรียบเทียบโมระกับคำอ่านที่บันทึกไว้ หมายเหตุภาษาไทยที่มีคำญี่ปุ่นเพิ่มเติมและขาดคำอ่านแสดงในรายการตรวจ ส่วนคำถามที่ทดสอบรูปร่างและกลุ่มตัวอักษรเพื่อเปรียบเทียบเป็นองค์ประกอบภาพของบทเรียน ตัวเลือกที่เป็น kana ในโจทย์คำอ่านมีแหล่งอ้างอิงถึงตัวเลือกโดยตรง

ถ้าต้องทำ manifest ฉบับผลิตซ้ำจากข้อมูลชุดเดิม ให้ใช้ `reading-decisions.json` และ `engine-query-overrides.json` กับ manifest ฐานที่มี SHA-256 ตรงกัน ตั้งชื่อผลลัพธ์ใหม่ในโฟลเดอร์เดิมเพื่อใช้ WAV ที่มีอยู่

```powershell
$audioBase = 'private/audio-voicevox'
python -X utf8 scripts/prepare_japanese_audio_release.py resolve `
  --decisions "$audioBase/reading-decisions.json" `
  --overrides "$audioBase/engine-query-overrides.json" `
  --output "$audioBase/production-manifest-rebuild.json"
```

## สร้าง MP3 และตรวจชุดไฟล์

ติดตั้ง FFmpeg สำหรับ Windows ให้เรียก `ffmpeg -version` ได้จาก PowerShell หรือส่งพาธ `ffmpeg.exe` ผ่าน `--ffmpeg` สคริปต์เก็บ WAV ต้นฉบับไว้และสร้าง MP3 mono ที่ 64 kbps ใน `mp3/` จากนั้นถอดรหัสเพื่อเทียบจำนวนตัวอย่างเสียงกับ WAV ตรวจความใกล้เคียงของสัญญาณ และบันทึก SHA-256 ทั้งสองรูปแบบ [ดาวน์โหลด FFmpeg](https://ffmpeg.org/download.html)

```powershell
$audioBase = 'private/audio-voicevox'
python -X utf8 scripts/prepare_japanese_audio_release.py package `
  --manifest "$audioBase/production-manifest.json" `
  --log "$audioBase/sample-run.jsonl" `
  --log "$audioBase/production-baseline.jsonl" `
  --log "$audioBase/production-final.jsonl" `
  --output "$audioBase/release-recheck"
```

เพิ่ม `--log` สำหรับแต่ละรอบที่สร้าง WAV เพิ่ม การตรวจ WAV ต้องมีรายงานรอบที่สร้างไฟล์จริงเพื่อเทียบโมระและ SHA-256 ถ้ารันซ้ำให้เลือกชื่อโฟลเดอร์รายงานใหม่ สคริปต์จะตรวจไฟล์ MP3 ที่มีอยู่และนำกลับมาใช้ ผลลัพธ์มี `mapping.json`, `audit.json`, `packaging.jsonl` และ `pronunciation-review.csv` พาธ WAV และ MP3 ใน mapping อิงจาก `private/audio-voicevox/`

## สำรองและเพิ่มเนื้อหาในอนาคต

ก่อนย้ายเครื่อง ให้สำรอง `private/audio-voicevox/` รวม WAV, MP3, manifest ทั้งสองรุ่น, ผลตัดสินคำอ่าน, ค่าแก้ query, รายงานทุกรอบ และผลฟังที่ผู้ตรวจบันทึกไว้ เว้นไฟล์คีย์ `.env.storage` จากชุดสำรองเสียง เก็บสำเนาที่มีสิทธิ์เข้าถึงจำกัด ตรวจ SHA-256 ของไฟล์ที่กู้คืนกับ `release/mapping.json` สำรองใบยืนยันการเผยแพร่, SQLite snapshot, รุ่นแก้ไขบรรณาธิการ และพจนานุกรมพร้อมไฟล์ SHA-256 ใต้ `private/` ถ้าต้องสร้าง manifest จากแหล่งเดิมอีกครั้ง ติดตั้ง VOICEVOX และ FFmpeg บนเครื่องใหม่และตรวจ voice ID ด้วย `probe`

เมื่อเพิ่มหมวดหรือ JLPT N5–N1 ให้ใช้ `content_id` เดิมกับเนื้อหาเดิม เพิ่มหมวดและระดับใน `content[].catalog` ของ manifest ฉบับผลิตใหม่ และเก็บแหล่งอ้างอิงใน `content[].references` ระบุระดับจากแหล่งข้อมูลของรุ่นนั้น คำหรือวลีใหม่ต้องมีคำอ่านและหลักฐานของตนเอง `audio_id` ขึ้นกับเสียงที่เลือกและข้อมูลสังเคราะห์ จึงใช้ WAV และ MP3 เดิมได้เมื่อค่าดังกล่าวตรงกัน เมื่อเสียงเดียวกันต่างบริบท ให้ตรวจการลงเสียงแยกตามการใช้งานก่อนอนุมัติคลิปร่วม

## แผนเชื่อมต่อ Supabase Storage และ React

1. หลังอนุมัติการฟังและสิทธิ์เผยแพร่ ให้ส่งออกเฉพาะรายการ MP3 ที่อนุมัติพร้อม SHA-256 ใช้พาธแบบ `ja/metan-normal/<audio_id>/<mp3-sha256>.mp3` และ `Content-Type: audio/mpeg` ตั้งค่า cache ตามอายุเผยแพร่ เปลี่ยนพาธเมื่อไฟล์เปลี่ยนเพื่อให้เปิดรุ่นก่อนหน้าได้ ใช้ public bucket เฉพาะคลิปที่อนุญาตให้เปิดสาธารณะ สำหรับคลิปจำกัดสิทธิ์ให้ใช้ private bucket กับ signed URL เก็บคีย์อัปโหลดไว้ฝั่งผู้ดูแล [Supabase Storage buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals) · [Supabase Smart CDN](https://supabase.com/docs/guides/storage/cdn/smart-cdn)
2. ให้ React ใช้ mapping ที่กรองเฉพาะ `content_id` ที่อนุมัติและ URL ของไฟล์นั้น ใช้แหล่งอ้างอิงของบทเพื่อจับคู่ปุ่มฟังกับคำอ่าน คำศัพท์ หรือประโยค เปิดเสียงเมื่อผู้เรียนกดปุ่ม และแสดงคำอธิบายปุ่มสำหรับเทคโนโลยีช่วยการเข้าถึง ในข้อทดสอบคำอ่าน ให้ส่ง mapping ที่เปิดเผยคำตอบหลังผู้เรียนส่งคำตอบตามกติกาของแบบทดสอบ
3. ใช้ `release/audit.json` วางแผนพื้นที่และปริมาณข้อมูล พื้นที่ของเว็บคิดจากผลรวมขนาด MP3 ที่อนุมัติ ปริมาณข้อมูลต่อรอบคำนวณจากขนาดไฟล์ที่เล่นจริงและจำนวนครั้งที่ดาวน์โหลด ตรวจเงื่อนไขของเสียงแล้วแสดงเครดิต `VOICEVOX:四国めたん` ในเว็บไซต์ [ข้อกำหนด VOICEVOX](https://voicevox.hiroshiba.jp/term/) · [หน้าทางการของเสียง 四国めたん](https://voicevox.hiroshiba.jp/product/shikoku_metan/)

### อัปโหลด MP3 ที่อนุมัติให้เผยแพร่

ใช้ bucket `kanji-japanese-audio` แบบ public จำกัดชนิดไฟล์เป็น `audio/mpeg` และขนาด 1 MiB ต่อไฟล์ ให้สิทธิ์เขียนเฉพาะฝั่งผู้ดูแล สคริปต์อ่าน URL จาก `backend/.env` หรือ `SUPABASE_URL` ใน PowerShell ควรตรงกับ `VITE_SUPABASE_URL` ของ frontend วางคีย์ลับของโปรเจกต์ในตัวแปร `SUPABASE_STORAGE_SECRET_KEY` ของ shell หรือไฟล์ `private/audio-voicevox/.env.storage` โดยใช้ชื่อตัวแปรเดียวกัน ไฟล์นี้อยู่ในโฟลเดอร์ที่ Git ข้าม เก็บคีย์ไว้เฉพาะเครื่องผู้ดูแล [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control)

```powershell
python -X utf8 scripts/publish_japanese_audio.py prepare
python -X utf8 scripts/publish_japanese_audio.py upload
python -X utf8 scripts/publish_japanese_audio.py verify
```

`prepare` ตรวจ SHA-256 ของไฟล์ทั้ง 604 รายการและสร้างดัชนีสำหรับตรวจใน `private/` คำสั่ง `upload` ใช้ `audio_id` และ SHA-256 เป็นพาธ ถ้าไฟล์เดิมตรงกัน ระบบจะข้ามไป ถ้าข้อมูลไม่ตรงกัน ระบบจะแจ้งข้อผิดพลาดและเก็บไฟล์เดิมไว้ รันคำสั่งเดิมเพื่อทำต่อได้ `verify` ดาวน์โหลดผ่าน URL สาธารณะและตรวจ SHA-256 โดยใช้ URL เพียงอย่างเดียว ทั้งสองคำสั่งเขียนรายงาน JSONL ใต้ `private/audio-voicevox/`

เมื่อดาวน์โหลดและตรวจครบ สคริปต์จะสร้าง `frontend/public/japanese-audio/index.json` ดัชนีสาธารณะเก็บคีย์แฮชสำหรับค้นหาตามบทและพาธ MP3 โดยตัดข้อความบทเรียน ข้อมูลภายใน และข้อมูลตัวเลือกข้อสอบออก ให้รวมเฉพาะดัชนีนี้ในชุด build ของ frontend เมื่อได้รับอนุญาตให้เผยแพร่แอป ถ้ายังไม่มีดัชนี หน้าเรียนเปิดได้ตามปกติและจะยังไม่มีปุ่มฟังเสียง

การอนุมัติเผยแพร่ไฟล์เสียงเป็นการอนุมัติใช้ชุดไฟล์ที่มีอยู่ สถานะการตรวจฟังรายคลิปยังเป็น `pending` ในรายงาน แหล่งอ้างอิงบทที่ 3 กล่าวถึง `明日` โดยไม่ได้ระบุว่าจะอ่าน `あした` `あす` หรือ `みょうにち` จึงไม่มีปุ่มฟังสำหรับการกล่าวถึงครั้งนั้น เมื่อบทอื่นระบุคำอ่านอย่างชัดเจน ปุ่มจะใช้ไฟล์ของคำอ่านที่ตรงกัน
