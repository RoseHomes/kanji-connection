import { createContext, useContext } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
export const LessonReturnContext = createContext("");
export function useLessonReturn() {
  return useContext(LessonReturnContext);
}
export function withLessonReturn(path: string, lesson: string) {
  if (!lesson) return path;
  return (
    path +
    (path.includes("?") ? "&" : "?") +
    "returnTo=" +
    encodeURIComponent(lesson)
  );
}
export function safeLessonReturn(value: string | null, slug?: string) {
  if (!value || !value.startsWith("/lessons/")) return null;
  try {
    const u = new URL(value, "http://lesson.local");
    if (
      u.origin !== "http://lesson.local" ||
      !/^\/lessons\/[a-z0-9-]+$/.test(u.pathname) ||
      (slug && u.pathname !== `/lessons/${slug}`)
    )
      return null;
    return u.pathname + u.search + u.hash;
  } catch {
    return null;
  }
}
export function useReturnHref(slug: string) {
  const [p] = useSearchParams();
  return safeLessonReturn(p.get("returnTo"), slug) || `/lessons/${slug}`;
}
export function ReturnToLesson() {
  const [p] = useSearchParams();
  const href = safeLessonReturn(p.get("returnTo"));
  return href ? (
    <Link className="text-link return-to-lesson" to={href}>
      <ArrowLeft size={17} />
      กลับไปยังช่วงที่กำลังเรียน
    </Link>
  ) : null;
}
