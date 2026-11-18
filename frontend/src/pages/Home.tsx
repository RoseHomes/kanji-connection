import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Eye,
  Layers,
  GitCompareArrows,
  Brain,
  BookOpen,
} from "lucide-react";
import { api } from "../api";
import type { Kanji, Lesson } from "../types";
import { DataState, EmptyState, SectionTitle } from "../components";

export default function Home() {
  const [active, setActive] = useState(0);
  const cards = useQuery({
    queryKey: ["public-preview"],
    queryFn: () => api<Kanji[]>("/kanjis?limit=3", { anonymous: true }),
  });
  const lessons = useQuery({
    queryKey: ["public-featured"],
    queryFn: () => api<Lesson[]>("/lessons?limit=3", { anonymous: true }),
  });
  const publicCards = cards.data?.filter((item) =>
    ["published", "sample", "verified_sample"].includes(item.review_status),
  );
  const card = publicCards?.[active] ?? publicCards?.[0];
  return (
    <>
      <section className="page home-hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="accent-line" /> A NEW WAY TO NOTICE
          </p>
          <h1>
            คันจิที่เคยไกลตัว
            <br />
            <em>ค่อย ๆ เข้าใจ</em>
            <br />
            ได้ทีละความเชื่อมโยง<span className="hero-period">。</span>
          </h1>
          <p className="hero-description">
            ให้เวลากับตัวอักษร สังเกตรูปร่าง อ่านความหมาย
            <br className="desktop-break" /> แล้วลองทดสอบความเข้าใจในจังหวะของคุณเอง
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/lessons">
              เลือกบทเรียน <ArrowRight size={18} />
            </Link>
            <Link className="text-link" to="/explore">
              สำรวจคันจิ <ArrowUpRight size={18} />
            </Link>
          </div>
          <p className="hero-note">
            <BookOpen size={16} /> เนื้อหาที่เผยแพร่แล้ว เรียนได้โดยไม่ต้องเข้าสู่ระบบ
          </p>
        </div>
        <div className="study-preview">
          <div className="preview-top">
            <span lang="ja">一歩ずつ</span>
            <span>LEARNING, AT YOUR PACE</span>
          </div>
          <div className="character-grid" aria-hidden={!card} lang="ja">
            {card?.character || "学"}
          </div>
          {card ? (
            <>
              <p className="preview-reading" lang="ja">
                {card.kunyomi.join(" · ") || card.onyomi.join(" · ")}
              </p>
              <h2>{card.meaning_th}</h2>
              <div className="demo-tabs" aria-label="เลือกคันจิ">
                {publicCards?.map((item, index) => (
                  <button
                    key={item.character}
                    lang="ja"
                    aria-pressed={active === index}
                    onClick={() => setActive(index)}
                  >
                    {item.character}
                  </button>
                ))}
              </div>
              <Link
                className="text-link"
                to={`/explore/${encodeURIComponent(card.character)}`}
              >
                เปิดบัตรคันจิ <ArrowUpRight size={16} />
              </Link>
            </>
          ) : (
            <div className="preview-empty">
              <p>พื้นที่เล็ก ๆ สำหรับความเข้าใจใหม่</p>
              <small>ตัวอักษรตกแต่ง · บัตรเรียนจะแสดงเมื่อมีเนื้อหาเผยแพร่</small>
            </div>
          )}
          <DataState
            loading={cards.isPending}
            error={cards.error}
            retry={() => void cards.refetch()}
          />
          <div className="preview-footer">
            <span>OBSERVE · CONNECT · REMEMBER</span>
            <span className="seal" aria-hidden="true">
              木
            </span>
          </div>
        </div>
      </section>
      <section className="method-band">
        <div className="page method-inner">
          <div className="method-intro">
            <p className="eyebrow">THE METHOD</p>
            <h2>
              ไม่ต้องรีบจำ
              <br />
              เริ่มจากการสังเกต
            </h2>
          </div>
          {[
            { icon: Eye, title: "สังเกต", body: "ให้เวลากับรูปร่างของตัวอักษร" },
            {
              icon: Layers,
              title: "เชื่อมโยง",
              body: "อ่านส่วนประกอบและคำอธิบายในบท",
            },
            {
              icon: GitCompareArrows,
              title: "เปรียบเทียบ",
              body: "วางตัวอักษรที่เรียนไว้ข้างกัน",
            },
            { icon: Brain, title: "ลองทบทวน", body: "ใช้แบบฝึกหัดตรวจความเข้าใจ" },
          ].map(({ icon: Icon, title, body }, i) => (
            <div className="method" key={title}>
              <span className="method-index">0{i + 1}</span>
              <Icon size={23} />
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="page section">
        <SectionTitle
          eyebrow="YOUR NEXT CHAPTER"
          title="เปิดบทเรียน แล้วค่อย ๆ เรียนรู้"
          to="/lessons"
        />
        <DataState
          loading={lessons.isPending}
          error={lessons.error}
          retry={() => void lessons.refetch()}
        />
        {lessons.data?.length === 0 && (
          <EmptyState title="บทเรียนสาธารณะกำลังเตรียมพร้อม">
            <p>
              เราจะเปิดบทเรียนเมื่อผ่านการตรวจสอบและอนุมัติเผยแพร่แล้ว
              <br />
              ไม่จำเป็นต้องสมัครบัญชีเพื่อรอเปิดอ่าน
            </p>
            <Link className="text-link" to="/explore">
              ไปยังคลังคันจิ <ArrowRight size={16} />
            </Link>
          </EmptyState>
        )}
        <div className="lesson-grid">
          {lessons.data
            ?.filter(
              (l) =>
                l.is_available &&
                ["published", "sample"].includes(l.status) &&
                !l.private_development,
            )
            .map((l) => (
              <Link
                className="lesson-card available"
                key={l.id}
                to={`/lessons/${l.slug}`}
              >
                <div className="lesson-card-top">
                  <span>บทที่ {String(l.chapter ?? l.id).padStart(2, "0")}</span>
                  <span className="pill">
                    {l.status === "sample" ? "ตัวอย่าง" : "พร้อมเรียน"}
                  </span>
                </div>
                <div className="lesson-glyphs" lang="ja">
                  {l.anchors.slice(0, 4).join(" ")}
                </div>
                <h3>{l.title_th}</h3>
                <p>{l.summary_th}</p>
                <div className="lesson-card-bottom">
                  <span>{l.available_count} ตัวอักษร</span>
                  <ArrowUpRight size={20} />
                </div>
              </Link>
            ))}
        </div>
      </section>
      <section className="page discovery-grid">
        <Link className="discovery-card" to="/explore">
          <p className="eyebrow">THE CHARACTER LIBRARY</p>
          <h2>เจอตัวอักษรที่อยากรู้จัก?</h2>
          <p>
            ค้นหาคันจิ คำอ่าน และความหมาย
            <br />
            เปิดดูรายละเอียดได้ทีละตัว
          </p>
          <span className="text-link">
            ไปสำรวจคันจิ <ArrowUpRight size={18} />
          </span>
        </Link>
        <Link className="discovery-card practice-discovery" to="/quiz">
          <p className="eyebrow">A MOMENT TO PRACTICE</p>
          <h2>ลองตอบ ก่อนเปิดเฉลย</h2>
          <p>
            ทำแบบฝึกหัดที่พร้อมเผยแพร่
            <br />
            ดูผลรอบนี้ได้โดยไม่ต้องมีบัญชี
          </p>
          <span className="text-link">
            เลือกแบบฝึกหัด <ArrowUpRight size={18} />
          </span>
        </Link>
      </section>
      <section className="page closing">
        <p className="eyebrow">MAKE ROOM FOR LEARNING</p>
        <h2>เริ่มเล็ก ๆ ก็เป็นการเริ่มต้นที่ดี</h2>
        <p>เรียนได้โดยไม่สมัครบัญชี เข้าสู่ระบบเมื่อต้องการใช้พื้นที่ส่วนตัว</p>
        <Link className="button" to="/account">
          รู้จักพื้นที่การเรียนรู้ของคุณ <ArrowRight size={17} />
        </Link>
      </section>
    </>
  );
}
