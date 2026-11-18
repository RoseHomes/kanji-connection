import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { api } from "../api";
import { DataState, EmptyState, KanjiVisual, Reading } from "../components";
import type { Kanji } from "../types";
interface Vocabulary {
  id: number;
  written_form: string;
  reading: string;
  meaning_th: string;
  usage_notes: string;
}
interface Relations {
  related: string[];
  relations?: { character: string; type: string; explanation_th: string }[];
}
export default function KanjiDetail() {
  const { character = "" } = useParams();
  const path = `/kanjis/${encodeURIComponent(character)}`;
  const card = useQuery({
    queryKey: ["public-kanji", character],
    queryFn: () => api<Kanji>(path, { anonymous: true }),
  });
  const vocabulary = useQuery({
    queryKey: ["public-vocabulary", character],
    queryFn: () =>
      api<Vocabulary[]>(`${path}/vocabulary?limit=100`, { anonymous: true }),
    enabled: !!card.data,
  });
  const relations = useQuery({
    queryKey: ["public-relations", character],
    queryFn: () => api<Relations>(`${path}/relations`, { anonymous: true }),
    enabled: !!card.data,
  });
  return (
    <div className="page section">
      <Link className="text-link" to="/explore">
        <ArrowLeft size={16} /> กลับไปคลังคันจิ
      </Link>
      <DataState
        loading={card.isPending}
        error={card.error}
        retry={() => void card.refetch()}
      />
      {card.data && (
        <>
          <div className="kanji-detail-header">
            <KanjiVisual character={card.data.character} />
            <div>
              <p className="eyebrow">A CLOSER LOOK</p>
              <h1>{card.data.meaning_th}</h1>
              <dl className="reading-list">
                <dt>คุนโยมิ</dt>
                <dd lang="ja">{card.data.kunyomi.join(" · ") || "—"}</dd>
                <dt>อนโยมิ</dt>
                <dd lang="ja">{card.data.onyomi.join(" · ") || "—"}</dd>
                {card.data.strokes !== null && (
                  <>
                    <dt>จำนวนขีด</dt>
                    <dd>{card.data.strokes}</dd>
                  </>
                )}
                {card.data.component && (
                  <>
                    <dt>ส่วนประกอบ</dt>
                    <dd lang="ja">{card.data.component}</dd>
                  </>
                )}
              </dl>
              {card.data.note_th && <p>{card.data.note_th}</p>}
              {/^https?:\/\//.test(card.data.source_url) && (
                <a
                  className="text-link"
                  href={card.data.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  ดูแหล่งอ้างอิง <ArrowUpRight size={16} />
                </a>
              )}
            </div>
          </div>
          <section className="lesson-section">
            <h2>คำศัพท์ที่มีตัวอักษรนี้</h2>
            <DataState
              loading={vocabulary.isPending}
              error={vocabulary.error}
              retry={() => void vocabulary.refetch()}
            />
            {vocabulary.data?.length === 0 && (
              <EmptyState title="ยังไม่มีตัวอย่างคำศัพท์ที่เผยแพร่สำหรับตัวนี้" />
            )}
            <div className="vocabulary-list">
              {vocabulary.data?.map((v) => (
                <article className="vocabulary-item" key={v.id}>
                  <Reading text={v.written_form} reading={v.reading} />
                  <p>{v.meaning_th}</p>
                  {v.usage_notes && <small>{v.usage_notes}</small>}
                </article>
              ))}
            </div>
          </section>
          <section className="lesson-section">
            <h2>ความเชื่อมโยง</h2>
            <DataState
              loading={relations.isPending}
              error={relations.error}
              retry={() => void relations.refetch()}
            />
            {relations.data?.related.length === 0 && (
              <p className="subtle">ยังไม่มีความสัมพันธ์ที่เผยแพร่สำหรับตัวนี้</p>
            )}
            <div className="related-list">
              {relations.data?.related.map((c) => (
                <Link
                  key={c}
                  to={`/explore/${encodeURIComponent(c)}`}
                  lang="ja"
                >
                  {c}
                </Link>
              ))}
            </div>
            {relations.data?.relations
              ?.filter((r) => r.explanation_th)
              .map((r, i) => (
                <p key={i}>
                  <span lang="ja">{r.character}</span> · {r.explanation_th}
                </p>
              ))}
            {relations.data && relations.data.related.length > 0 && (
              <Link
                className="button"
                to={`/compare?characters=${encodeURIComponent([character, ...relations.data.related.slice(0, 3)].join(","))}`}
              >
                เปิดดูข้างกัน <ArrowUpRight size={16} />
              </Link>
            )}
          </section>
        </>
      )}
    </div>
  );
}
