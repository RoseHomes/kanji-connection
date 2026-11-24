import { Link } from "react-router-dom";
import { useId } from "react";
import { ArrowUpRight, Lightbulb, GitCompareArrows } from "lucide-react";
import { AudioContentRow, KanjiCard, Reading, ReadingAudioRow } from "./components";
import type { ComparisonItem, Kanji, LessonSection, SourceCard } from "./types";
import { useLessonReturn, withLessonReturn } from "./lesson-return";
import { AudioText, LessonAudioButton } from "./lesson-audio";
const titles: Record<string, string> = {
  introduction: "สิ่งที่ควรสังเกต",
  cards: "ทำความรู้จักตัวอักษร",
  comparison: "วางข้างกัน แล้วดูความต่าง",
  mnemonic: "ความสัมพันธ์ที่ช่วยให้จำ",
  vocabulary: "คำศัพท์ที่เชื่อมความหมาย",
  exercises: "ถึงเวลาลองด้วยตัวเอง",
};
function Node({ item }: { item: ComparisonItem }) {
  const study = item.study_reading;
  const reading = study ? study.reading : item.reading;
  const kind = study ? study.kind : item.kind;
  return (
    <div className="diagram-node">
      <span className="comparison-glyph" lang="ja">
        {item.kanji}
      </span>
      {item.kind === "component" && <small>ส่วนประกอบ</small>}
      <AudioContentRow audio={reading && (
        <LessonAudioButton
          kind={kind === "component" ? "component" : kind === "word" ? "word" : "kanji"}
          text={study?.form ?? item.kanji}
          reading={reading}
        />
      )}>
        {study && <small>{study.label_th}</small>}
        {study && kind !== "component" ? (
          <Reading text={study.form} reading={reading} />
        ) : reading && <small lang="ja">{reading}</small>}
        <strong>{item.meaning_th || item.label_th}</strong>
      </AudioContentRow>
    </div>
  );
}
export function LessonSections({
  sections,
  kanjis,
  slug,
  showToc = true,
  focused = false,
  allowDetails = false,
  activeCharacter,
  showAllCards = false,
}: {
  sections: LessonSection[];
  kanjis: Kanji[];
  slug: string;
  showToc?: boolean;
  focused?: boolean;
  allowDetails?: boolean;
  activeCharacter?: string;
  showAllCards?: boolean;
}) {
  const returnTo = useLessonReturn();
  const uid = useId();
  const sectionId = (i: number) =>
    showToc ? `lesson-section-${i}` : `content-${uid}-${i}`;
  const renderCard = (c: SourceCard) => {
    const k = kanjis.find((k) => k.character === c.character);
    return k ? (
      <KanjiCard
        key={c.character}
        item={k}
        source={c}
        focused={focused}
        allowDetail={allowDetails}
      />
    ) : (
      <article className="kanji-card" key={c.character}>
        <Node item={{ kanji: c.character, meaning_th: c.meaning_th }} />
        <p>{c.memory_note}</p>
      </article>
    );
  };
  const renderChoice = (c: SourceCard) =>
    activeCharacter ? (
      <div
        className={`learning-card-item ${c.character === activeCharacter ? "is-selected" : ""}`}
        key={c.character}
        data-card-character={c.character}
      >
        {renderCard(c)}
      </div>
    ) : (
      renderCard(c)
    );
  return (
    <>
      {showToc && (
        <nav className="lesson-toc" aria-label="เนื้อหาในบทนี้">
          {sections.map((s, i) => (
            <a key={i} href={`#lesson-section-${i}`}>
              {s.kind === "cards"
                ? `ตัวอักษรชุด ${sections.slice(0, i + 1).filter((x) => x.kind === "cards").length}`
                : titles[s.kind] || s.kind}
            </a>
          ))}
        </nav>
      )}
      {sections.map((section, i) => (
        <section
          className={`lesson-section section-${section.kind} ${activeCharacter ? "focused-cards" : ""} ${showAllCards ? "show-all" : ""}`}
          id={sectionId(i)}
          key={i}
          aria-labelledby={`${sectionId(i)}-title`}
        >
          <div className="section-title">
            <h2 id={`${sectionId(i)}-title`}>
              {titles[section.kind] || section.kind}
            </h2>
            {section.kind === "cards" && (
              <span className="count-label">ค่อย ๆ รู้จักทีละตัว</span>
            )}
          </div>
          {section.blocks.map((b, j) => (
            <div key={j}>
              {b.text && <p><AudioText text={b.text} /></p>}
              {b.instructions_th && (
                <p className="learner-instructions"><AudioText text={b.instructions_th} /></p>
              )}
              {section.kind === "introduction" && (
                <div className="orientation">
                  <Lightbulb size={24} />
                  <p>
                    {b.subtitle_th ||
                      "เริ่มจากรูป คำอ่าน และความหมาย แล้วลองเทียบตัวที่คล้ายกัน อย่าเดาคำอ่านทั้งคำจากคันจิตัวเดียว"}
                  </p>
                </div>
              )}
              {b.cards && (
                <>
                  <div className="kanji-grid">
                    {b.cards
                      .filter((c) => c.study?.role !== "supplementary")
                      .map(renderChoice)}
                  </div>
                  {b.cards.some((c) => c.study?.role === "supplementary") && (
                    <aside
                      className="supplementary-study"
                      aria-label="ตัวอักษรเสริม"
                    >
                      <span className="supplement-label">เลือกเรียนได้</span>
                      <h3>อีกนิด สำหรับคนอยากรู้เพิ่ม</h3>
                      <p>ดูความสัมพันธ์ของรูปได้ โดยไม่ต้องท่องรูปสะกดที่พบไม่บ่อย</p>
                      <div className="kanji-grid">
                        {b.cards
                          .filter((c) => c.study?.role === "supplementary")
                          .map(renderChoice)}
                      </div>
                    </aside>
                  )}
                </>
              )}
              {b.pairs && (
                <div className="pair-grid">
                  {b.pairs.map((pair, p) => (
                    <article className="comparison-pair" key={p}>
                      <div className="pair-characters">
                        {pair.map((s, n) => (
                          <div className="pair-endpoint" key={s.kanji}>
                            {n > 0 && <span className="pair-versus">↔</span>}
                            <Node item={s} />
                          </div>
                        ))}
                      </div>
                      <Link className="text-link" to={withLessonReturn(
                        `/compare?characters=${encodeURIComponent(pair.map((s) => s.kanji).join(","))}`, returnTo,
                      )}>
                        เปิดตารางเปรียบเทียบ
                        <ArrowUpRight size={15} />
                      </Link>
                    </article>
                  ))}
                </div>
              )}
              {b.memory_tips && (
                <div className="lesson-memory">
                  <span className="icon-tile">
                    <Lightbulb size={24} />
                  </span>
                  <div>
                    <h3>จุดสังเกตที่ลองนำไปใช้ได้</h3>
                    <ul className="memory-tips">
                      {b.memory_tips.map((t, n) => (
                        <li key={n}><AudioText text={t} /></li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
              {b.diagram && (
                <div className="relationship-panel">
                  <p>มองส่วนรูปที่เหมือนกัน แล้วเชื่อมโยงกับคำที่เรียน</p>
                  {b.diagram.core ? (
                    <div className="mnemonic-network">
                      <Node item={b.diagram.core} />
                      <span className="network-arrow" aria-hidden="true">
                        ↓
                      </span>
                      <div className="diagram-neighbors">
                        {b.diagram.related.map((s, n) => (
                          <Node item={s} key={n} />
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="network-pairs">
                      {b.diagram.comparison_pairs.map((pair, n) => (
                        <Link
                          to={withLessonReturn(
                            `/compare?characters=${encodeURIComponent(pair.map((s) => s.kanji).join(","))}`,
                            returnTo,
                          )}
                          key={n}
                        >
                          <GitCompareArrows size={18} />
                          <span lang="ja">
                            {pair.map((s) => s.kanji).join(" ↔ ")}
                          </span>
                          <ArrowUpRight size={16} />
                        </Link>
                      ))}
                    </div>
                  )}
                  <small>ความเชื่อมโยงเพื่อช่วยจำ ไม่ใช่ข้อสรุปเรื่องประวัติอักษร</small>
                </div>
              )}
              {b.vocabulary && (
                <div className="vocabulary-list">
                  {b.vocabulary.map((v, n) => (
                    <article className="vocabulary-item" key={n}>
                      <ReadingAudioRow text={v.word} reading={v.reading} kind="word">
                        <p>{v.meaning_th}</p>
                      </ReadingAudioRow>
                      {v.usage_notes && (
                        <details>
                          <summary>คำนี้ใช้แบบไหน?</summary>
                          <p className="reading-scope"><AudioText text={v.usage_notes} /></p>
                        </details>
                      )}
                    </article>
                  ))}
                </div>
              )}
              {!!b.sentences?.length && (
                <div className="sentence-section">
                  <h3>จากคำ สู่ประโยคที่ใช้ได้</h3>
                  <div className="sentence-list">
                    {b.sentences.map((s, n) => (
                      <article className="sentence-card" key={n}>
                        <ReadingAudioRow text={s.text} reading={s.reading} kind="sentence">
                          <p>{s.meaning_th}</p>
                        </ReadingAudioRow>
                        {s.source_url && (
                          <details>
                            <summary>แหล่งเรียนรู้เพิ่มเติม</summary>
                            <a
                              href={s.source_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              ดูตัวอย่างการใช้จากแหล่งสอนภาษาญี่ปุ่น ↗
                            </a>
                          </details>
                        )}
                      </article>
                    ))}
                  </div>
                </div>
              )}
              {section.kind === "exercises" && (
                <div className="practice-invitation">
                  <span className="stamp" lang="ja">
                    思
                  </span>
                  <div>
                    <h3>ลองดูว่าจำความต่างได้แค่ไหน</h3>
                    <p>เลือกคำตอบทีละข้อ พร้อมคำอธิบายและโอกาสทบทวนข้อที่ยังสับสน</p>
                    <Link
                      className="button primary"
                      to={withLessonReturn(`/quiz/${slug}`, returnTo)}
                    >
                      เริ่มข้อสอบเลือกตอบ
                      <ArrowUpRight size={18} />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
