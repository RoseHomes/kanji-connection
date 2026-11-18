import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Kanji } from "../types";
import {
  DataState,
  KanjiVisual,
  PrivateNotice,
  EmptyState,
} from "../components";
import { useAuth } from "../auth";
export default function Compare() {
  const { session, ready } = useAuth();
  const [params, setParams] = useSearchParams();
  const picker = useQuery({
    queryKey: ["comparison-picker", session?.user.id],
    queryFn: () =>
      api<Kanji[]>("/learning/kanjis?limit=24", { anonymous: !session }),
    enabled: ready || !session,
  });
  const selected = (
    params.get("characters") ??
    picker.data
      ?.slice(0, 2)
      .map((k) => k.character)
      .join(",") ??
    ""
  )
    .split(",")
    .filter(Boolean);
  const [input, setInput] = useState(selected.join(","));
  const inputEdited = useRef(false);
  const [message, setMessage] = useState("");
  const selectionKey = selected.join(",");
  useEffect(() => {
    if (!inputEdited.current) setInput(selectionKey);
    setMessage("");
  }, [selectionKey]);
  const valid =
    selected.length >= 2 &&
    selected.length <= 4 &&
    new Set(selected).size === selected.length &&
    selected.every((c) => Array.from(c).length === 1);
  function choose(chars: string[]) {
    inputEdited.current = false;
    setParams({ characters: chars.join(",") });
    setInput(chars.join(","));
    setMessage("");
  }
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["compare", session?.user.id, selected],
    queryFn: () =>
      api<Kanji[]>(
        `/learning/compare?characters=${encodeURIComponent(selected.join(","))}`,
        { anonymous: !session },
      ),
    enabled: (ready || !session) && valid,
  });
  return (
    <div className="page section">
      <p className="eyebrow">SIDE BY SIDE</p>
      <h1>ยิ่งมองใกล้ ยิ่งเห็นความต่าง</h1>
      <p className="lead">เลือก 2–4 ตัวเพื่อเทียบรูปร่าง การอ่าน และความหมาย</p>
      <form
        className="comparison-form"
        onSubmit={(e) => {
          e.preventDefault();
          const chars = [...new Set(input.split(/[\s,、，]+/).filter(Boolean))];
          if (
            chars.length < 2 ||
            chars.length > 4 ||
            chars.some((c) => Array.from(c).length !== 1)
          ) {
            setMessage("ใส่คันจิ 2–4 ตัว คั่นด้วยช่องว่างหรือจุลภาค");
            return;
          }
          choose(chars);
        }}
      >
        <label htmlFor="compare-characters">ตัวอักษรที่ต้องการเปรียบเทียบ</label>
        <div>
          <input
            id="compare-characters"
            value={input}
            maxLength={30}
            onChange={(e) => {
              inputEdited.current = true;
              setInput(e.target.value);
            }}
            lang="ja"
          />
          <button type="submit">เปรียบเทียบ</button>
        </div>
      </form>
      {(message || (!valid && params.has("characters"))) && (
        <p role="alert">{message || "ลิงก์นี้ต้องระบุคันจิ 2–4 ตัว"}</p>
      )}
      <div className="filters" role="group" aria-label="เลือกคันจิสำหรับเปรียบเทียบ">
        {picker.data?.map(({ character: c }) => (
          <button
            key={c}
            lang="ja"
            aria-pressed={selected.includes(c)}
            disabled={
              (selected.includes(c) && selected.length === 2) ||
              (!selected.includes(c) && selected.length >= 4)
            }
            onClick={() =>
              choose(
                selected.includes(c)
                  ? selected.filter((x) => x !== c)
                  : [...selected, c],
              )
            }
          >
            {c}
          </button>
        ))}
      </div>
      <DataState
        loading={picker.isPending || (valid && isPending)}
        error={error || picker.error}
        retry={() => {
          void refetch();
          void picker.refetch();
        }}
      />
      {picker.data?.length === 0 && !params.has("characters") && (
        <EmptyState title="ยังไม่มีคันจิที่เผยแพร่ให้เปรียบเทียบ">
          <p>เมื่อมีบัตรที่ผ่านการอนุมัติแล้ว คุณจะเลือกดูข้างกันได้ที่นี่</p>
        </EmptyState>
      )}
      <div className="compare-grid">
        {data?.map((k) => (
          <article className="comparison" key={k.character}>
            <KanjiVisual character={k.character} meaning={k.meaning_th} />
            <dl>
              <dt>คุนโยมิ</dt>
              <dd lang="ja">{k.kunyomi.join("・") || "—"}</dd>
              <dt>อนโยมิ</dt>
              <dd lang="ja">{k.onyomi.join("・") || "—"}</dd>
              <dt>จำนวนขีด</dt>
              <dd>{k.strokes ?? "ยังไม่ระบุ"}</dd>
              <dt>ส่วนประกอบที่สังเกต</dt>
              <dd lang="ja">{k.component || "—"}</dd>
            </dl>
            <p>{k.note_th}</p>
          </article>
        ))}
      </div>
      {data?.some(
        (k) =>
          !["published", "sample", "verified_sample"].includes(k.review_status),
      ) && <PrivateNotice />}
      {data &&
        data.length > 1 &&
        data[0].component &&
        data.every((k) => k.component === data[0].component) && (
          <aside className="notice">
            <strong>ส่วนประกอบร่วมที่ระบุในข้อมูล</strong>
            <p lang="ja">{data[0].component}</p>
          </aside>
        )}
    </div>
  );
}
