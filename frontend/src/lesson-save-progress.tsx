import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuth } from "./auth";
import { DataState } from "./components";
import type { DashboardData } from "./learning-types";
import type { Health } from "./types";

export function LessonSaveProgress({ slug }: { slug: string }) {
  const { session } = useAuth();
  const ownerId = session?.user.id;
  const cache = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health", { anonymous: true }),
    enabled: !!ownerId,
  });
  const writable = !!ownerId && health.data?.account_writes_enabled === true;
  const key = ["dashboard", ownerId];
  const dashboard = useQuery({
    queryKey: key,
    queryFn: () => api<DashboardData>("/me/dashboard", { ownerId }),
    enabled: writable,
  });
  const progress = dashboard.data?.lessons.find(
    (lesson) => lesson.slug === slug,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!ownerId) return null;
  if (!writable)
    return health.error ? (
      <DataState
        loading={false}
        error={health.error}
        retry={() => void health.refetch()}
      />
    ) : null;

  async function save() {
    if (!dashboard.data || saving) return;
    setSaving(true);
    setError("");
    try {
      await api(`/me/progress/${slug}`, {
        ownerId,
        method: "PUT",
        body: JSON.stringify({
          progress: 100,
          expected_version: progress?.version ?? 0,
        }),
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      await cache.invalidateQueries({ queryKey: key });
      setSaving(false);
    }
  }

  return (
    <div>
      <DataState
        loading={dashboard.isPending}
        error={dashboard.error}
        retry={() => void dashboard.refetch()}
      />
      {error && <p role="alert">{error}</p>}
      {progress?.progress === 100 ? (
        <p role="status" className="subtle">
          บันทึกในบัญชีแล้ว · อ่านจบบทนี้
        </p>
      ) : (
        dashboard.data && (
          <button type="button" disabled={saving} onClick={() => void save()}>
            {saving ? "กำลังบันทึก…" : "บันทึกว่าอ่านจบบทนี้"}
          </button>
        )
      )}
    </div>
  );
}
