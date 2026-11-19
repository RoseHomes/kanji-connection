import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, ArrowUpRight, GitCompareArrows } from "lucide-react";
import { api } from "../api";
import { DataState, EmptyState, Reading } from "../components";
import { Chips, PageHeading, Reveal } from "../ui";
import { ChoicePicker } from "../selection-controls";
import { ReturnToLesson } from "../lesson-return";
import {
  chapterGroup,
  learningGroups,
  type ComparisonGroup,
} from "../presentation-types";
export default function Compare() {
  const [params, setParams] = useSearchParams();
  const [category, setCategory] = useState("all");
  const [partner, setPartner] = useState(1);
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 700px)").matches,
  );
  useEffect(() => {
    const q = window.matchMedia("(max-width: 700px)");
    const f = () => setMobile(q.matches);
    q.addEventListener("change", f);
    return () => q.removeEventListener("change", f);
  }, []);
  const groups = useQuery({
    queryKey: ["comparison-groups"],
    queryFn: () => api<ComparisonGroup[]>("/learning/comparison-groups"),
  });
  const filtered =
    groups.data?.filter(
      (g) => category === "all" || chapterGroup(g.chapter) === category,
    ) || [];
  const selected =
    filtered.find((g) => g.id === params.get("group")) ||
    filtered.find(
      (g) =>
        g.characters.map((c) => c.character).join(",") ===
        params.get("characters"),
    ) ||
    filtered[0];
  const pick = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("group", id);
    next.delete("characters");
    setParams(next, { replace: true, preventScrollReset: true });
    setPartner(1);
    if (mobile)
      requestAnimationFrame(() =>
        document.querySelector(".comparison-workspace")?.scrollIntoView({
          block: "start",
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "auto"
            : "smooth",
        }),
      );
  };
  const columns = selected
    ? mobile && selected.characters.length > 2
      ? [
          selected.characters[0],
          selected.characters[
            Math.min(partner, selected.characters.length - 1)
          ],
        ]
      : selected.characters
    : [];
  return (
    <div className="page section compare-page">
      <ReturnToLesson />
      <PageHeading eyebrow="SPOT THE DIFFERENCE" title="คล้ายตรงไหน ต่างตรงนี้">
        <p>เลือกชุดคันจิ แล้วดูความต่างข้างกันได้ทันที ไม่ต้องพิมพ์</p>
      </PageHeading>
      <DataState
        loading={groups.isPending}
        error={groups.error}
        retry={() => void groups.refetch()}
      />
      {groups.data?.length === 0 && (
        <EmptyState title="ชุดเปรียบเทียบกำลังเตรียมพร้อม">
          <p>เมื่อมีบทเรียนที่เข้าถึงได้ ชุดที่เกี่ยวข้องจะแสดงที่นี่</p>
          <Link className="button primary" to="/lessons">
            เลือกบทเรียน
          </Link>
        </EmptyState>
      )}
      {!!groups.data?.length && (
        <>
          <Chips
            label="หมวดชุดเปรียบเทียบ"
            items={learningGroups}
            value={category}
            onChange={(v) => {
              setCategory(v);
              const first = groups.data.find(
                (g) => v === "all" || chapterGroup(g.chapter) === v,
              );
              if (first) pick(first.id);
            }}
          />
          {!filtered.length && (
            <EmptyState title="ยังไม่มีชุดในหมวดนี้">
              <button
                onClick={() => {
                  setCategory("all");
                  const next = new URLSearchParams(params);
                  next.delete("group");
                  next.delete("characters");
                  setParams(next);
                }}
              >
                ดูชุดทั้งหมด
              </button>
            </EmptyState>
          )}
          <div className="comparison-layout">
            <aside className="group-directory" id="choose-groups">
              <div className="section-title">
                <h2>เลือกชุดที่อยากรู้จัก</h2>
                <span>{filtered.length} ชุด</span>
              </div>
              <ChoicePicker
                label="เลือกบทเปรียบเทียบ"
                value={selected?.id || ""}
                options={filtered.map((g) => ({
                  value: g.id,
                  label: `บท ${g.chapter} · ${g.title}`,
                  description: g.category,
                }))}
                onChange={pick}
              />
              <div className="group-buttons" role="group" aria-label="ชุดคันจิ">
                {filtered.map((g) => (
                  <button
                    key={g.id}
                    aria-pressed={selected?.id === g.id}
                    className={
                      selected?.id === g.id
                        ? "group-pick selected"
                        : "group-pick"
                    }
                    onClick={() => pick(g.id)}
                  >
                    <span lang="ja">{g.title}</span>
                    <small>
                      บท {String(g.chapter).padStart(2, "0")} · {g.category}
                    </small>
                  </button>
                ))}
              </div>
            </aside>
            {selected && (
              <Reveal key={selected.id} className="comparison-workspace">
                <div className="comparison-heading">
                  <span className="icon-tile">
                    <GitCompareArrows size={24} />
                  </span>
                  <div>
                    <p className="eyebrow">มองรูปเดียวกันให้ต่างออกไป</p>
                    <h2 lang="ja">{selected.title}</h2>
                    <p className="sr-only" role="status" aria-live="polite">
                      กำลังแสดงตาราง {selected.title}
                    </p>
                  </div>
                </div>
                {mobile && selected.characters.length > 2 && (
                  <Chips
                    label="เลือกคู่ที่แสดง"
                    items={selected.characters.slice(1).map((c, i) => ({
                      value: String(i + 1),
                      label: `${selected.characters[0].character} / ${c.character}`,
                    }))}
                    value={String(partner)}
                    onChange={(v) => setPartner(Number(v))}
                  />
                )}
                <div className="comparison-table-wrap">
                  <table className="comparison-table">
                    <caption>
                      คำอ่าน ความหมาย และจุดสังเกตของ {selected.title}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">มองใกล้อีกนิด</th>
                        {columns.map((c) => (
                          <th scope="col" key={c.character}>
                            <span className="table-glyph" lang="ja">
                              {c.character}
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <th scope="row">คำอ่าน</th>
                        {columns.map((c) => (
                          <td key={c.character}>
                            <small>{c.reading.label_th}</small>
                            {c.reading.kind === "component" ? (
                              <span lang="ja">{c.reading.reading}</span>
                            ) : (
                              <Reading
                                text={c.reading.form}
                                reading={c.reading.reading}
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">ความหมาย</th>
                        {columns.map((c) => (
                          <td key={c.character}>
                            <strong>{c.meaning_th}</strong>
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">
                          ภาพช่วยจำ
                          <br />
                          และส่วนรูป
                        </th>
                        {columns.map((c) => (
                          <td key={c.character}>{c.memory_note}</td>
                        ))}
                      </tr>
                      <tr>
                        <th scope="row">คำตัวอย่าง</th>
                        {columns.map((c) => (
                          <td key={c.character}>
                            {c.example ? (
                              <>
                                <Reading
                                  text={c.example.word}
                                  reading={c.example.reading}
                                />
                                <p>{c.example.meaning_th}</p>
                                {c.example.optional && (
                                  <small className="supplement-label">
                                    คำเสริม · เลือกเรียนได้
                                  </small>
                                )}
                              </>
                            ) : (
                              <span>ดูชื่อส่วนประกอบและรูปในบทเรียน</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div className="difference-note">
                  <strong>จุดสังเกตเมื่อวางข้างกัน</strong>
                  <p>{selected.difference_th}</p>
                </div>
                <div className="hero-actions">
                  <Link
                    className="button primary"
                    to={`/quiz/${selected.slug}`}
                  >
                    ฝึกแยกตัวอักษร
                    <ArrowRight size={17} />
                  </Link>
                  <Link
                    className="button secondary"
                    to={`/lessons/${selected.slug}`}
                  >
                    ดูในบทเรียน
                    <ArrowUpRight size={17} />
                  </Link>
                  <a
                    className="text-link"
                    href="#choose-groups"
                    onClick={() =>
                      document
                        .querySelector<HTMLSelectElement>(
                          ".select-label select",
                        )
                        ?.focus()
                    }
                  >
                    เลือกชุดอื่น
                  </a>
                </div>
              </Reveal>
            )}
          </div>
        </>
      )}
    </div>
  );
}
