import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Search, LockKeyhole } from "lucide-react";
import { api } from "../api";
import type { Lesson } from "../types";
import { DataState, PrivateNotice } from "../components";
import { useAuth } from "../auth";
export const parts = [
  "ทั้งหมด",
  "รากฐาน",
  "การประกอบ",
  "ตัวคล้าย",
  "ส่วนประกอบ",
  "ขั้นต่อไป",
  "ชีวิตจริง",
];
export default function Catalog() {
  const { session, ready } = useAuth();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const part = /^[1-6]$/.test(params.get("part") || "")
    ? params.get("part")!
    : "";
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["lessons", session?.user.id, q, part],
    queryFn: () =>
      api<Lesson[]>(
        `/learning/catalog?q=${encodeURIComponent(q)}${part ? `&part=${encodeURIComponent(part)}` : ""}`,
      ),
    enabled: ready,
  });
  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }
  return (
    <div className="page section">
      <p className="eyebrow">THE CURRICULUM</p>
      <h1>เส้นทางการเรียนรู้</h1>
      <p className="lead">30 บท · 6 หมวด · ค่อย ๆ สร้างความเข้าใจจากรากฐาน</p>
      {data?.some((l) => l.private_development) ? (
        <PrivateNotice />
      ) : (
        <p className="notice">
          เลือกบทที่พร้อมเรียนเพื่อเริ่มต้น เนื้อหาที่อยู่ระหว่างตรวจสอบยังไม่เปิดให้อ่าน
        </p>
      )}
      <label className="search-box">
        <Search size={20} />
        <input
          maxLength={100}
          aria-label="ค้นหาบทเรียน"
          placeholder="ค้นหาชื่อบทเรียน หรือคันจิ…"
          value={q}
          onChange={(e) => update("q", e.target.value)}
        />
      </label>
      <div className="filters" aria-label="หมวดบทเรียน">
        {parts.map((p, i) => (
          <button
            key={p}
            aria-pressed={part === (i ? String(i) : "")}
            onClick={() => update("part", i ? String(i) : "")}
          >
            {p}
          </button>
        ))}
      </div>
      <DataState
        loading={isPending}
        error={error}
        retry={() => void refetch()}
      />
      {data?.length === 0 && (
        <div className="notice" role="status">
          {q || part ? (
            <>
              <p>ไม่พบบทเรียนที่ตรงกับคำค้น</p>
              <button onClick={() => setParams({})}>ล้างตัวกรอง</button>
            </>
          ) : (
            <>
              <p>ยังไม่มีบทเรียนที่เปิดให้บัญชีนี้เข้าถึง เนื้อหาที่ยังตรวจไม่เสร็จจะไม่เผยแพร่</p>
              {!session && (
                <Link className="text-link" to="/account">
                  เข้าสู่ระบบเพื่อดูสิทธิ์ของบัญชี
                </Link>
              )}
            </>
          )}
        </div>
      )}
      <div className="lesson-grid">
        {data?.map((l) => (
          <article
            className={`lesson-card ${l.is_available ? "available" : ""}`}
            key={l.id}
          >
            <div className="lesson-card-top">
              <span>บทที่ {String(l.chapter ?? l.id).padStart(2, "0")}</span>
              <small>
                {l.private_development
                  ? "ส่วนตัว · รอตรวจ"
                  : l.is_available
                    ? l.status === "sample"
                      ? "ตัวอย่างพร้อมเรียน"
                      : "พร้อมเรียน"
                    : "รอตรวจสอบ"}
              </small>
            </div>
            <div className="lesson-glyphs" lang="ja">
              {l.anchors.slice(0, 4).join(" ") || "復習"}
            </div>
            <h2>{l.title_th}</h2>
            <p>{l.summary_th}</p>
            <div className="lesson-card-bottom">
              <small>
                {l.available_count} ตัวอักษร
                {l.private_development ? "ในบทนี้" : "พร้อมเรียน"}
              </small>
              {l.is_available ? (
                <Link to={`/lessons/${l.slug}`}>
                  เริ่มเรียน <ArrowUpRight size={16} />
                </Link>
              ) : (
                <span>
                  <LockKeyhole size={14} /> ยังไม่เผยแพร่
                </span>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
