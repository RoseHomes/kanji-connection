import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../api";
import type { Kanji } from "../types";
import { DataState, KanjiCard } from "../components";
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
      ),
    enabled: ready,
  });
  return (
    <div className="page section">
      <p className="eyebrow">KANJI EXPLORER</p>
      <h1>รู้จักทีละตัว เชื่อมโยงทีละนิด</h1>
      <p className="lead">
        ค้นหาคันจิ ความหมายไทย คานะ หรือโรมาจิ ในเนื้อหาที่บัญชีนี้เข้าถึงได้
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
        แสดงเฉพาะบัตรคำสอน · เนื้อหาส่วนตัวและคำแปลที่รอตรวจยังไม่ถือว่าผ่านการอนุมัติ
      </p>
      {data?.length === 0 && (
        <p role="status">
          {q
            ? "ไม่พบคันจิที่ตรงกับคำค้น ลองเปลี่ยนหรือล้างคำค้น"
            : "ยังไม่มีบัตรคันจิที่เปิดให้บัญชีนี้เข้าถึง"}
        </p>
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
