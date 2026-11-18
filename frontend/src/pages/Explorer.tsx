import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../api";
import type { Kanji } from "../types";
import { DataState, KanjiCard, EmptyState } from "../components";
import { useAuth } from "../auth";
export default function Explorer() {
  const { session, ready } = useAuth();
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["kanjis", session?.user.id, q, offset],
    queryFn: () =>
      api<Kanji[]>(
        `/learning/kanjis?q=${encodeURIComponent(q)}&offset=${offset}&limit=31`,
        { anonymous: !session },
      ),
    enabled: ready || !session,
  });
  return (
    <div className="page section">
      <p className="eyebrow">KANJI EXPLORER</p>
      <h1>รู้จักทีละตัว เชื่อมโยงทีละนิด</h1>
      <p className="lead">
        ค้นหาจากตัวอักษร ความหมายไทย คานะ หรือโรมาจิ · เปิดอ่านได้โดยไม่ต้องมีบัญชี
      </p>
      <label className="search-box">
        <Search size={20} />
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
          maxLength={100}
          aria-label="ค้นหาคันจิ"
          placeholder="ลอง 木, ป่า, はやし หรือ mori"
        />
      </label>
      <DataState
        loading={isPending}
        error={error}
        retry={() => void refetch()}
      />
      <p className="subtle">
        เลือกบัตรเพื่อเปิดดูคำศัพท์และความเชื่อมโยงที่พร้อมให้เรียน
      </p>
      {data?.length === 0 && (
        <EmptyState
          title={
            q
              ? "ไม่พบคันจิที่ตรงกับคำค้น ลองเปลี่ยนหรือล้างคำค้น"
              : "คลังคันจิสาธารณะกำลังเตรียมพร้อม"
          }
        >
          {q ? (
            <button
              onClick={() => {
                setQ("");
                setOffset(0);
              }}
            >
              ล้างคำค้น
            </button>
          ) : (
            "บัตรคันจิที่ผ่านการอนุมัติจะปรากฏที่นี่ โดยไม่ต้องเข้าสู่ระบบ"
          )}
        </EmptyState>
      )}
      <div className="kanji-grid">
        {data?.slice(0, 30).map((k) => (
          <KanjiCard key={k.character} item={k} />
        ))}
      </div>
      {(offset > 0 || (data?.length || 0) > 30) && (
        <nav className="pagination" aria-label="หน้ารายการคันจิ">
          <button
            disabled={offset === 0 || isPending}
            onClick={() => setOffset(Math.max(0, offset - 30))}
          >
            ก่อนหน้า
          </button>
          <span>หน้า {Math.floor(offset / 30) + 1}</span>
          <button
            disabled={!data || data.length <= 30 || isPending}
            onClick={() => setOffset(offset + 30)}
          >
            ถัดไป
          </button>
        </nav>
      )}
    </div>
  );
}
