import { Reading } from "./components";
import type { SourceCard } from "./types";
import { Disclosure } from "./disclosure";

export function StudyContent({
  card,
  focused = false,
}: {
  card: SourceCard;
  focused?: boolean;
}) {
  const study = card.study;
  if (!study) return null;
  const example = study.example;
  const exampleBody = example && (
    <div className="study-example" data-example-role={example.role}>
      <Reading text={example.word} reading={example.reading} />
      {example.meaning_th && <p lang="th">{example.meaning_th}</p>}
      <p className="reading-scope">{example.target_scope}</p>
    </div>
  );
  return (
    <div className="study-content">
      <div className="study-reading" data-reading-kind={study.reading.kind}>
        <small>{study.reading.label_th}</small>
        {study.reading.kind === "component" ? (
          <p lang="ja">{study.reading.reading}</p>
        ) : (
          <Reading text={study.reading.form} reading={study.reading.reading} />
        )}
        {!focused && <p className="reading-scope">{study.reading.note_th}</p>}
      </div>
      {example?.optional ? (
        <details className="optional-example">
          <summary>
            {example.role === "proper_name"
              ? "ตัวอย่างชื่อสถานที่ · เลือกเรียนได้"
              : "ตัวอย่างเสริม · ไม่ต้องท่องจำ"}
          </summary>
          {exampleBody}
        </details>
      ) : example ? (
        <div className="core-example">
          <small>
            {example.role === "component_demo"
              ? "พบส่วนประกอบนี้ใน"
              : "คำศัพท์ในบริบท"}
          </small>
          {exampleBody}
        </div>
      ) : null}
      {!focused && study.scope_note_th && study.role !== "supplementary" && (
        <p className="scope-note">{study.scope_note_th}</p>
      )}
      <div className="mnemonic-cue">
        <strong>มองรูปแล้วเชื่อมความหมาย</strong>
        <p>{card.memory_note}</p>
        {!focused && <small>{study.mnemonic_note_th}</small>}
      </div>
      {focused && (
        <Disclosure label="รายละเอียดคำอ่านและภาพจำ">
          <p>{study.reading.note_th}</p>
          {study.scope_note_th && study.role !== "supplementary" && (
            <p>{study.scope_note_th}</p>
          )}
          <p>{study.mnemonic_note_th}</p>
        </Disclosure>
      )}
    </div>
  );
}
