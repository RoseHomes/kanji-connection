import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Kanji } from "../types";
import { DataState, KanjiVisual, PrivateNotice } from "../components";
import { useAuth } from "../auth";
export default function Compare() {
  const { session, ready } = useAuth();
  const [params, setParams] = useSearchParams();
  const selected = (params.get("characters") || "林,森").split(",");
  const [input, setInput] = useState(selected.join(","));
  const [message, setMessage] = useState("");
  const selectionKey = selected.join(",");
  useEffect(() => {
    setInput(selectionKey);
    setMessage("");
  }, [selectionKey]);
  const valid =
    selected.length >= 2 &&
    selected.length <= 4 &&
    new Set(selected).size === selected.length &&
    selected.every((c) => Array.from(c).length === 1);
  function choose(chars: string[]) {
    setParams({ characters: chars.join(",") });
    setInput(chars.join(","));
    setMessage("");
  }
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["compare", session?.user.id, selected],
    queryFn: () =>
      api<Kanji[]>(
        `/learning/compare?characters=${encodeURIComponent(selected.join(","))}`,
      ),
    enabled: ready && valid,
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
            onChange={(e) => setInput(e.target.value)}
            lang="ja"
          />
          <button type="submit">เปรียบเทียบ</button>
        </div>
      </form>
      {(message || !valid) && (
        <p role="alert">{message || "ลิงก์นี้ต้องระบุคันจิ 2–4 ตัว"}</p>
      )}
      <div className="filters">
        {["木", "林", "森"].map((c) => (
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
        loading={valid && isPending}
        error={error}
        retry={() => void refetch()}
      />
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
      {data && selected.every((c) => ["木", "林", "森"].includes(c)) && (
        <aside className="notice">
          <strong>ความสัมพันธ์: ส่วนประกอบเดียวกัน</strong>
          <p>
            林 มี 木 สองส่วนวางข้างกัน ส่วน 森 มี 木 สามส่วน
            วางหนึ่งส่วนด้านบนและสองส่วนด้านล่าง ภาพนี้ช่วยสังเกตรูปร่าง ไม่ใช่คำอธิบายลำดับขีด
          </p>
        </aside>
      )}
    </div>
  );
}
