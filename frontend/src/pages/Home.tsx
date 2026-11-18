import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Eye,
  Layers,
  GitCompareArrows,
  Brain,
  Sprout,
} from "lucide-react";
import { MemoryIllustration, SectionTitle } from "../components";
const demos = [
  {
    character: "木",
    meaning: "ต้นไม้",
    reading: "き · ki",
    count: 1,
    note: "เริ่มจากต้นไม้หนึ่งต้น สังเกตลำต้นและกิ่งก้าน",
  },
  {
    character: "林",
    meaning: "หมู่ต้นไม้",
    reading: "はやし · hayashi",
    count: 2,
    note: "木 สองตัวอยู่เคียงกัน ลองมองหาส่วนประกอบที่ซ้ำ",
  },
  {
    character: "森",
    meaning: "ป่าไม้",
    reading: "もり · mori",
    count: 3,
    note: "木 สามตัวรวมกัน ภาพช่วยจำของต้นไม้ที่หนาแน่น",
  },
];
export default function Home() {
  const [active, setActive] = useState(0);
  const demo = demos[active];
  return (
    <>
      <section className="hero page">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="tiny-line" /> มองคันจิ ให้เห็นความเชื่อมโยง
          </p>
          <h1>
            ไม่ใช่แค่จำคันจิ
            <br />
            แต่<span className="sage-text">เข้าใจ</span>ไปด้วยกัน
            <span className="hero-period">。</span>
          </h1>
          <p className="hero-description">
            จากภาพที่คุ้นเคย สู่ตัวอักษรที่เข้าใจ
            <br />
            เรียนรู้ผ่านส่วนประกอบ เปรียบเทียบตัวที่คล้าย
            <br />
            แล้วค่อย ๆ สร้างความทรงจำของคุณเอง
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/lessons">
              เลือกบทเรียน <ArrowRight size={18} />
            </Link>
            <Link className="text-link" to="/lessons">
              สำรวจบทเรียน <ArrowUpRight size={17} />
            </Link>
          </div>
          <div className="hero-note">
            <span className="mini-seal" lang="ja">
              学
            </span>
            <span>
              เริ่มจากสิ่งเล็ก ๆ แล้วต่อยอดทีละตัว
              <small>ภาษาไทย · ตัวอย่างสำหรับผู้เริ่มต้น</small>
            </span>
          </div>
        </div>
        <div className="hero-art">
          <span className="art-caption">
            A LITTLE CONNECTION, A LASTING MEMORY
          </span>
          <div className="paper-card">
            <div className="paper-top">
              <span>01 — มองภาพให้เป็นตัวอักษร</span>
              <Sprout size={19} />
            </div>
            <MemoryIllustration count={demo.count} />
            <div className="demo-glyph" lang="ja">
              {demo.character}
            </div>
            <p className="demo-reading" lang="ja">
              {demo.reading}
            </p>
            <h2>{demo.meaning}</h2>
            <div className="demo-tabs" aria-label="เลือกคันจิ">
              {demos.map((d, i) => (
                <button
                  key={d.character}
                  className={active === i ? "selected" : ""}
                  aria-pressed={active === i}
                  onClick={() => setActive(i)}
                  lang="ja"
                >
                  {d.character}
                </button>
              ))}
            </div>
            <p className="demo-note" aria-live="polite">
              {demo.note}
            </p>
            <span className="paper-foot">ภาพช่วยจำ · ไม่ใช่ลำดับการเขียน</span>
          </div>
          <span className="vertical-note" lang="ja">
            小さな一歩、大きなつながり。
          </span>
          <div className="floating-label">
            <span>木 + 木 = 林</span>
            <small>ยิ่งเห็นความเชื่อมโยง ยิ่งจำได้</small>
          </div>
        </div>
      </section>
      <section className="method-band">
        <div className="page method-inner">
          <p>
            จำด้วยความเข้าใจ
            <br />
            <strong>เรียนรู้ในแบบที่เป็นธรรมชาติ</strong>
          </p>
          {[
            { icon: Eye, n: "01", title: "สังเกต", sub: "มองรูปร่างให้คุ้นตา" },
            { icon: Layers, n: "02", title: "แยกส่วน", sub: "เห็นตัวเล็กในตัวใหญ่" },
            {
              icon: GitCompareArrows,
              n: "03",
              title: "เปรียบเทียบ",
              sub: "จับจุดที่ต่างกัน",
            },
            { icon: Brain, n: "04", title: "ทบทวน", sub: "เรียกคืนความทรงจำ" },
          ].map(({ icon: Icon, n, title, sub }) => (
            <div className="method" key={n}>
              <span className="method-icon">
                <Icon size={22} />
              </span>
              <div>
                <small>{n}</small>
                <h3>{title}</h3>
                <p>{sub}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="page section">
        <SectionTitle
          eyebrow="LEARN THROUGH CONNECTIONS"
          title="ตัวอักษรเล็ก ๆ เรื่องราวที่เชื่อมถึงกัน"
          to="/explore"
        />
        <div className="feature-grid">
          <Link to="/lessons" className="feature feature-trees">
            <span className="pill">บทเรียนตัวอย่าง · บทที่ 02</span>
            <div className="glyph-sequence" lang="ja">
              木 <span>→</span> 林 <span>→</span> 森
            </div>
            <h3>ตัวอย่างพร้อมลองในแอป</h3>
            <p>รู้จักส่วนประกอบที่ซ้ำ แล้วเชื่อมภาพกับความหมาย</p>
            <span className="feature-link">
              ลองเรียนรู้ <ArrowUpRight size={18} />
            </span>
          </Link>
          <Link to="/compare" className="feature feature-compare">
            <span className="pill">ลองเปรียบเทียบ</span>
            <div className="compare-teaser" lang="ja">
              <span>林</span>
              <i>／</i>
              <span>森</span>
            </div>
            <h3>มองคล้ายกัน ต่างกันตรงไหน?</h3>
            <p>วางข้างกัน แล้วสังเกตจำนวนและตำแหน่งของ 木</p>
            <span className="feature-link">
              เปิดโหมดเปรียบเทียบ <ArrowUpRight size={18} />
            </span>
          </Link>
        </div>
      </section>
      <section className="page curriculum-section">
        <div>
          <p className="eyebrow">YOUR LEARNING PATH</p>
          <h2>
            ค่อย ๆ ต่อภาพ
            <br />
            ให้เป็นความเข้าใจ
          </h2>
          <p>
            เส้นทาง 30 บท แบ่งเป็น 6 หมวด
            <br />
            ตั้งแต่รูปทรงพื้นฐานไปจนถึงคำในชีวิตประจำวัน
          </p>
          <Link className="text-link" to="/lessons">
            ดูเส้นทางการเรียน <ArrowRight size={18} />
          </Link>
        </div>
        <div className="path-list">
          {[
            "รากฐานของรูปทรง",
            "ประกอบตัวอักษร",
            "แยกแยะตัวคล้าย",
            "รู้จักส่วนประกอบ",
            "เชื่อมโยงขั้นต่อไป",
            "ใช้ในชีวิตจริง",
          ].map((title, i) => (
            <Link to={`/lessons?part=${i + 1}`} key={title}>
              <span className="path-number">0{i + 1}</span>
              <span>
                {title}
                <small>
                  บทที่ {i * 5 + 1}–{i * 5 + 5} · เปิดตามสิทธิ์และสถานะเนื้อหา
                </small>
              </span>
              <ArrowUpRight size={18} />
            </Link>
          ))}
        </div>
      </section>
      <section className="page closing">
        <Sprout size={32} />
        <h2>ความเข้าใจ เริ่มได้จากหนึ่งตัวอักษร</h2>
        <p>วันนี้ ลองรู้จัก 木 ให้มากกว่าเดิม</p>
        <Link className="button primary" to="/lessons">
          เลือกบทเรียนที่เข้าถึงได้ <ArrowRight size={17} />
        </Link>
      </section>
    </>
  );
}
