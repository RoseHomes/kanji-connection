import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { LessonDetail, Lesson as LessonMetadata } from "../types";
import { DataState } from "../components";
import { LessonExperience } from "../lesson-experience";
export default function Lesson() {
  const { slug } = useParams();
  const lesson = useQuery({
    queryKey: ["lesson", slug],
    queryFn: () => api<LessonDetail>(`/learning/lesson/${slug}`),
  });
  const catalog = useQuery({
    queryKey: ["learner-catalog"],
    queryFn: () => api<LessonMetadata[]>("/learning/catalog"),
  });
  return (
    <div className="page section hybrid-page">
      <DataState
        loading={lesson.isPending}
        error={lesson.error}
        retry={() => void lesson.refetch()}
      />
      {lesson.isPending && (
        <div className="lesson-skeleton" aria-hidden="true">
          <div />
          <div />
          <div />
        </div>
      )}
      {lesson.error && (
        <Link className="button" to="/lessons">
          กลับไปเลือกบทเรียนที่เข้าถึงได้
        </Link>
      )}
      {lesson.data && (
        <LessonExperience
          key={lesson.data.slug}
          lesson={lesson.data}
          catalog={catalog.data || []}
        />
      )}
    </div>
  );
}
