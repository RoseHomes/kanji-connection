import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { api } from "../api";
import {
  DataState,
  LoadingState,
  ReadOnlyNotice,
  PrivateNotice,
  AccountGate,
} from "../components";
import { Link } from "react-router-dom";
import type { Health } from "../types";
import { useAuth } from "../auth";
import type { CloudReview } from "../learning-types";
import { KanjiReadingList, useStopAudioOnChange } from "../lesson-audio";
interface Card {
  character: string;
  meaning_th: string;
  kunyomi: string[];
  onyomi: string[];
  schedule?: CloudReview | null;
  private_development?: boolean;
}
export default function Review() {
  const { session, ready } = useAuth();
  if (!ready)
    return (
      <div className="page section">
        <LoadingState>กำลังตรวจบัญชี…</LoadingState>
      </div>
    );
  if (!session)
    return (
      <AccountGate
        title="แฟลชการ์ดในจังหวะของคุณ"
        description="เข้าสู่ระบบเพื่อดูคิวทบทวนและผลการจำส่วนตัว ข้อมูลนี้จะผูกกับบัญชีของคุณเท่านั้น"
      />
    );
  return <PersonalReview />;
}
function PersonalReview() {
  const { session, ready } = useAuth();
  const cache = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health", { anonymous: true }),
  });
  const cloud = !!session && health.data?.content_mode === "database";
  const readOnly = !cloud || health.data?.account_writes_enabled !== true;
  const key = ["review-cards", session?.user.id, cloud];
  const { data, isPending, error, refetch } = useQuery({
    queryKey: key,
    queryFn: () => api<Card[]>(cloud ? "/me/review-cards" : "/kanjis"),
    enabled: ready && !!health.data,
  });
  const [queue, setQueue] = useState<string[] | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const due =
    data?.filter((k) => {
      const s = k.schedule;
      return !s || Date.parse(s.due) <= Date.now();
    }) || [];
  const chars = queue ?? due.map((k) => k.character);
  const card = data?.find((k) => k.character === chars[0]);
  useStopAudioOnChange(`${card?.character}:${revealed}`);
  async function answer(knew: boolean) {
    if (!card || busy || readOnly) return;
    setBusy(true);
    setMessage("");
    try {
      if (cloud) {
        const result = await api<CloudReview>(
          `/me/reviews/${encodeURIComponent(card.character)}`,
          {
            ownerId: session?.user.id,
            method: "PUT",
            body: JSON.stringify({
              knew,
              expected_version: card.schedule?.version || 0,
            }),
          },
        );
        cache.setQueryData<Card[]>(key, (old) =>
          old?.map((k) =>
            k.character === card.character ? { ...k, schedule: result } : k,
          ),
        );
        void cache.invalidateQueries({ queryKey: ["dashboard"] });
      }
      setQueue(knew ? chars.slice(1) : [...chars.slice(1), card.character]);
      setRevealed(false);
    } catch (e) {
      setMessage((e as Error).message);
      void refetch();
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page section review-page">
      <p className="eyebrow">A LITTLE EVERY DAY</p>
      <h1>ให้ความทรงจำค่อย ๆ เติบโต</h1>
      <p className="lead">
        {cloud
          ? "แฟลชการ์ดส่วนตัว · เซิร์ฟเวอร์คำนวณกำหนดทบทวน"
          : "ตัวอย่างบัตรคำ · ยังไม่พร้อมบันทึกกับบัญชี"}
      </p>
      <DataState
        loading={isPending || health.isPending}
        error={error || health.error}
        retry={() => {
          void refetch();
          void health.refetch();
        }}
      />
      {readOnly && <ReadOnlyNotice />}
      {data?.some((k) => k.private_development) && <PrivateNotice />}
      {message && (
        <p role="alert" className="notice">
          {message}
        </p>
      )}
      {card ? (
        <>
          <p className="subtle">เหลือในรอบนี้ {chars.length} ตัว</p>
          <button
            className="flashcard"
            disabled={busy}
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "ซ่อนคำตอบ" : "เปิดคำตอบ"}
            aria-expanded={revealed}
          >
            <span lang="ja">{card.character}</span>
            {revealed ? (
              <div>
                <h2>{card.meaning_th}</h2>
                {card.private_development && <p lang="ja">
                  {card.kunyomi.join("・")} / {card.onyomi.join("・")}
                </p>}
              </div>
            ) : (
              <p>แตะเพื่อเปิดคำตอบ</p>
            )}
          </button>
          {revealed && !card.private_development && (
            <dl className="review-audio-readings">
              <dt>คุนโยมิ</dt><dd><KanjiReadingList character={card.character} readings={card.kunyomi} /></dd>
              <dt>อนโยมิ</dt><dd><KanjiReadingList character={card.character} readings={card.onyomi} /></dd>
            </dl>
          )}
          {revealed && (
            <div className="review-actions">
              <button
                disabled={busy || readOnly}
                onClick={() => void answer(false)}
              >
                ยังจำไม่ได้ · ลองอีกครั้ง
              </button>
              <button
                className="primary"
                disabled={busy || readOnly}
                onClick={() => void answer(true)}
              >
                จำได้แล้ว ✓
              </button>
            </div>
          )}
        </>
      ) : (
        data &&
        !error && (
          <div className="notice content-stack">
            {data.length === 0 ? (
              <>
                <h2>ยังไม่มีบัตรคันจิที่เปิดให้เข้าถึง</h2>
                <Link className="text-link" to="/lessons">
                  ดูบทเรียนและสิทธิ์ของบัญชี
                </Link>
              </>
            ) : (
              <>
                <h2>ยังไม่มีการ์ดที่ถึงกำหนด 🌱</h2>
                <p>กลับมาทบทวนอีกครั้งตามกำหนด หรือฝึกชุดนี้ซ้ำได้</p>
                <div className="action-group">
                  <button
                    onClick={() => {
                      setQueue(data.map((k) => k.character));
                      setRevealed(false);
                    }}
                  >
                    <RotateCcw size={16} /> ฝึกอีกครั้ง
                  </button>
                </div>
              </>
            )}
          </div>
        )
      )}
      <p className="subtle">
        จำได้: นัดครั้งแรก 1 วัน แล้วเพิ่มเป็นสองเท่า สูงสุด 90 วัน
        <br />
        จำไม่ได้: ลองซ้ำในรอบนี้ และนัดใหม่ใน 1 วัน · ประเมินความจำด้วยตนเอง
      </p>
    </div>
  );
}
