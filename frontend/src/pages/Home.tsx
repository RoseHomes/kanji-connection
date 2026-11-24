import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AudioText, useStopAudioOnChange } from "../lesson-audio";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Eye,
  GitCompareArrows,
  Brain,
  CircleCheck,
} from "lucide-react";
import { AnimatePresence, m, useReducedMotion } from "motion/react";
import { api } from "../api";
import type { Lesson } from "../types";
import type { ComparisonGroup } from "../presentation-types";
import { ComparisonReading, DataState, EmptyState, Reading } from "../components";
import { Reveal } from "../ui";
export default function Home() {
  const reduce = useReducedMotion();
  const lessons = useQuery({
    queryKey: ["featured-catalog"],
    queryFn: () => api<Lesson[]>("/learning/catalog"),
  });
  const groups = useQuery({
    queryKey: ["comparison-groups"],
    queryFn: () => api<ComparisonGroup[]>("/learning/comparison-groups"),
  });
  const [active, setActive] = useState(0);
  const group =
    groups.data?.find((g) => g.characters.length === 3) || groups.data?.[0];
  const card = group?.characters[active % group.characters.length];
  useStopAudioOnChange(card?.character);
  return (
    <>
      <section className="page home-hero">
        <Reveal className="hero-copy">
          <p className="eyebrow">
            <span className="tiny-sun" /> SMALL DETAILS. BIG CONNECTIONS.
          </p>
          <h1>
            คล้ายกันนิดเดียว
            <br />
            <span className="hero-highlight">เข้าใจต่างกันได้</span>
            <span className="coral">。</span>
          </h1>
          <p className="hero-description">
            เปลี่ยนคันจิที่ดูเหมือนกัน ให้เป็นความเชื่อมโยงที่จำได้
            <br />
            มองรูป ดูความต่าง แล้วลองเลือกคำตอบด้วยตัวเอง
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/lessons">
              เริ่มเรียน
              <ArrowRight size={19} />
            </Link>
            <Link className="button secondary" to="/compare">
              สำรวจคู่เปรียบเทียบ
              <ArrowUpRight size={19} />
            </Link>
          </div>
          <p className="hero-note">
            <CircleCheck size={16} /> ไม่ต้องมีแป้นญี่ปุ่น · ฝึกได้โดยไม่ต้องเข้าสู่ระบบ
          </p>
        </Reveal>
        <Reveal className="hero-art">
          <div className="art-caption">
            <span>THE ART OF NOTICING</span>
            <span className="stamp" lang="ja">
              学
            </span>
          </div>
          {card && group ? (
            <>
              <div
                className="hero-kanji-pickers"
                role="group"
                aria-label="ลองสังเกตตัวคันจิ"
              >
                {group.characters.map((c, i) => (
                  <button
                    key={c.character}
                    aria-pressed={active === i}
                    onClick={() => setActive(i)}
                    className={
                      active === i ? "motif-card active" : "motif-card"
                    }
                  >
                    <span lang="ja">{c.character}</span>
                  </button>
                ))}
              </div>
              <AnimatePresence mode="wait" initial={false}>
                <m.div
                  key={card.character}
                  className="motif-note"
                  initial={{ opacity: 0, y: reduce ? 0 : 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: reduce ? 0 : 0.18 }}
                >
                  <ComparisonReading item={card} slug={group.slug} />
                  <strong>{card.meaning_th}</strong>
                  <p><AudioText text={card.memory_note} slug={group.slug} /></p>
                </m.div>
              </AnimatePresence>
              <Link className="text-link" to={`/compare?group=${group.id}`}>
                ลองดูความต่างให้ชัดขึ้น
                <ArrowUpRight size={17} />
              </Link>
            </>
          ) : groups.isPending || groups.error ? (
            <DataState
              loading={groups.isPending}
              error={groups.error}
              retry={() => void groups.refetch()}
            />
          ) : (
            <div className="hero-empty">
              <Reading text="つながる" reading="つながる" audioKind="word" />
              <p>ทุกความเข้าใจ เริ่มจากการสังเกต</p>
              <small>ชุดเรียนรู้จะแสดงเมื่อมีบทเรียนที่เข้าถึงได้</small>
            </div>
          )}
          <span className="art-orbit" aria-hidden="true" />
        </Reveal>
      </section>
      <section className="page method-section">
        <div className="section-title">
          <div>
            <p className="eyebrow">FOUR SMALL STEPS</p>
            <h2>จำได้ เพราะเข้าใจความสัมพันธ์</h2>
          </div>
          <p>เรียนในจังหวะของคุณเอง</p>
        </div>
        <div className="method-grid">
          {[
            {
              icon: Eye,
              title: "เรียนรูป",
              text: "เริ่มจากตัวอักษร คำอ่าน และความหมาย",
            },
            {
              icon: GitCompareArrows,
              title: "ดูความต่าง",
              text: "วางตัวคล้ายกัน แล้วมองจุดสังเกต",
            },
            {
              icon: Brain,
              title: "ฝึกจำ",
              text: "เชื่อมรูปกับภาพและคำศัพท์ที่มีความหมาย",
            },
            {
              icon: CircleCheck,
              title: "ทดสอบ",
              text: "เลือกคำตอบ ดูเหตุผล แล้วลองทบทวน",
            },
          ].map(({ icon: Icon, title, text }, i) => (
            <article className="method-tile" key={title}>
              <span className="step-number">0{i + 1}</span>
              <Icon size={21} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="page section">
        <div className="section-title">
          <div>
            <p className="eyebrow">YOUR NEXT CONNECTION</p>
            <h2>เริ่มต้นจากบทเล็ก ๆ</h2>
          </div>
          <Link className="text-link" to="/lessons">
            ดูบทเรียนทั้งหมด
            <ArrowUpRight size={18} />
          </Link>
        </div>
        <DataState
          loading={lessons.isPending}
          error={lessons.error}
          retry={() => void lessons.refetch()}
        />
        {lessons.data?.length === 0 && (
          <EmptyState title="บทเรียนสาธารณะกำลังเตรียมพร้อม">
            <p>เมื่อบทเรียนได้รับอนุมัติแล้ว คุณจะเริ่มเรียนได้ที่นี่โดยไม่ต้องสมัครบัญชี</p>
            <Link to="/explore" className="button secondary">
              สำรวจเนื้อหาที่พร้อมเรียน
            </Link>
          </EmptyState>
        )}
        <div className="lesson-grid">
          {lessons.data?.slice(0, 3).map((l) => (
            <Link
              className="lesson-card"
              to={`/lessons/${l.slug}`}
              key={l.slug}
            >
              <div className="card-topline">
                <span>LESSON {String(l.chapter).padStart(2, "0")}</span>
                <ArrowUpRight size={20} />
              </div>
              <div className="chapter-glyphs" lang="ja">
                {l.anchors.slice(0, 3).join(" ")}
              </div>
              <h3>{l.title_th}</h3>
              <p>{l.summary_th}</p>
              <div className="card-bottom">
                <span>{l.available_count} ตัวอักษร</span>
                <strong>เริ่มเรียน →</strong>
              </div>
            </Link>
          ))}
        </div>
      </section>
      <section className="page">
        <aside className="home-cta">
          <div>
            <p className="eyebrow">NOTICE SOMETHING NEW TODAY</p>
            <h2>
              ไม่ต้องจำทุกอย่างในวันเดียว
              <br />
              แค่เห็นความต่างเพิ่มอีกนิด
            </h2>
          </div>
          <Link className="button dark" to="/compare">
            ลองเปรียบเทียบ
            <ArrowUpRight size={20} />
          </Link>
          <span className="cta-symbol" aria-hidden="true" lang="ja">
            見
          </span>
        </aside>
      </section>
    </>
  );
}
