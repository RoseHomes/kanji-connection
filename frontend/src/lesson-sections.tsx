import { Link } from "react-router-dom";
import { KanjiCard, Reading } from "./components";
import type { ComparisonItem, Kanji, LessonSection } from "./types";

const titles: Record<string, string> = {
  introduction: "ภาพรวมบทเรียน",
  cards: "บัตรคันจิ",
  comparison: "เปรียบเทียบรูปร่าง",
  mnemonic: "แผนภาพช่วยจำ",
  vocabulary: "คำศัพท์",
  exercises: "แบบฝึกหัด",
};
function Node({ item }: { item: ComparisonItem }) {
  return (
    <span className="diagram-node">
      <Reading text={item.kanji} reading={item.reading} />
      <span lang="th">{item.meaning_th || item.label_th}</span>
      {item.kind === "component" && <small>ส่วนประกอบ</small>}
    </span>
  );
}
function Pairs({ pairs }: { pairs: ComparisonItem[][] }) {
  return (
    <div className="pair-grid">
      {pairs.map((pair, i) => (
        <div className="comparison-pair" key={i} aria-label="คู่เปรียบเทียบ">
          {pair.map((item, j) => (
            <span className="pair-endpoint" key={j}>
              {j > 0 && <span aria-hidden="true">≠</span>}
              <Node item={item} />
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
export function LessonSections({
  sections,
  kanjis,
  slug,
}: {
  sections: LessonSection[];
  kanjis: Kanji[];
  slug: string;
}) {
  return (
    <>
      <nav className="lesson-toc" aria-label="เนื้อหาในบทนี้">
        {sections.map((s, i) => (
          <a key={i} href={`#lesson-section-${i}`}>
            {titles[s.kind] || s.kind}
            {s.kind === "cards"
              ? ` ${sections.slice(0, i + 1).filter((x) => x.kind === "cards").length}`
              : ""}
          </a>
        ))}
      </nav>
      {sections.map((section, i) => (
        <section
          className="lesson-section"
          id={`lesson-section-${i}`}
          key={i}
          aria-labelledby={`section-title-${i}`}
        >
          <div className="section-title">
            <h2 id={`section-title-${i}`}>
              {titles[section.kind] || section.kind}
            </h2>
            {section.pdf_pages.length > 0 && (
              <small className="subtle">
                PDF หน้า {section.pdf_pages.join(", ")}
              </small>
            )}
          </div>
          {section.blocks.map((b, j) => (
            <div key={j}>
              {b.subtitle_th && <p className="lead">{b.subtitle_th}</p>}
              {b.category && <p>{b.category}</p>}
              {b.cards && (
                <div className="kanji-grid">
                  {b.cards.map((c) => {
                    const k = kanjis.find((k) => k.character === c.character);
                    return k ? (
                      <KanjiCard key={c.character} item={k} source={c} />
                    ) : (
                      <article className="notice" key={c.character}>
                        <Node
                          item={{
                            kanji: c.character,
                            reading: c.reading_example,
                            meaning_th: c.meaning_th,
                          }}
                        />
                        <p>{c.memory_note}</p>
                      </article>
                    );
                  })}
                </div>
              )}
              {b.pairs && (
                <Pairs
                  pairs={
                    b.typed_comparisons?.map((pair) =>
                      pair.endpoints.map((e) => ({
                        kanji: e.glyph,
                        kind: e.kind,
                        reading: e.reading,
                        meaning_th: e.meaning_th,
                      })),
                    ) || b.pairs
                  }
                />
              )}
              {b.memory_tips && (
                <ul className="memory-tips">
                  {b.memory_tips.map((tip, n) => (
                    <li key={n}>{tip}</li>
                  ))}
                </ul>
              )}
              {b.diagram && (
                <>
                  <p className="subtle">
                    ภาพช่วยจำตามความสัมพันธ์ในแหล่งข้อมูล ·
                    ยังไม่ยืนยันว่าเป็นประวัติที่มาของอักษร
                  </p>
                  {b.diagram.core ? (
                    <div className="mnemonic-network">
                      <Node item={b.diagram.core} />
                      <span className="network-arrow" aria-hidden="true">
                        ↓
                      </span>
                      <div className="diagram-neighbors">
                        {b.diagram.related.map((node, n) => (
                          <Node key={n} item={node} />
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="notice">
                        แหล่งข้อมูลไม่ระบุแกนกลาง แสดงเฉพาะคู่เปรียบเทียบที่มีอยู่
                      </p>
                      <Pairs
                        pairs={
                          b.editorial_view?.pairs || b.diagram.comparison_pairs
                        }
                      />
                    </>
                  )}
                </>
              )}
              {b.vocabulary && (
                <div className="vocabulary-list">
                  {b.vocabulary.map((v, n) => (
                    <article className="vocabulary-item" key={n}>
                      <Reading text={v.word} reading={v.reading} />
                      <p lang="th">{v.meaning_th}</p>
                      <small>PDF หน้า {v.pdf_page}</small>
                    </article>
                  ))}
                </div>
              )}
              {b.exercises && (
                <>
                  <ol className="exercise-preview">
                    {b.exercises.map((q) => (
                      <li value={q.number} key={q.number}>
                        <span lang="ja">{q.prompt}</span>
                        <small>PDF หน้า {q.pdf_page}</small>
                      </li>
                    ))}
                  </ol>
                  {b.exercise_c_prompt && <p>{b.exercise_c_prompt}</p>}
                  <Link className="button primary" to={`/quiz/${slug}`}>
                    เปิดแบบฝึกหัดแบบโต้ตอบ
                  </Link>
                </>
              )}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
