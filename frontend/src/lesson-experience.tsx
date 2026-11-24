import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
  useNavigationType,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, m, useReducedMotion } from "motion/react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  Compass,
  GitCompareArrows,
  List,
  Play,
  RotateCcw,
} from "lucide-react";
import type { LessonDetail, Lesson as LessonMetadata } from "./types";
import type { PracticeQuestion, ComparisonGroup } from "./presentation-types";
import { api } from "./api";
import { DataState, Reading } from "./components";
import { LessonSections } from "./lesson-sections";
import {
  deriveStages,
  phases,
  readPosition,
  resolveStage,
  writePosition,
  type LessonStage,
} from "./lesson-stages";
import { ChoicePicker, SegmentedControl } from "./selection-controls";
import { Disclosure } from "./disclosure";
import { LessonReturnContext, withLessonReturn } from "./lesson-return";
import { PracticeRound } from "./pages/Quiz";
import { LessonSaveProgress } from "./lesson-save-progress";
import { LessonAudio, LessonAudioButton } from "./lesson-audio";

function QuickCheck({ slug, active }: { slug: string; active: boolean }) {
  const q = useQuery({
    queryKey: ["practice", slug],
    queryFn: () => api<PracticeQuestion[]>(`/learning/practice/${slug}?include_feedback=true`),
    enabled: active,
  });
  const questions = useMemo(
    () =>
      Array.isArray(q.data)
        ? q.data.filter((q) => q.kind !== "shape").slice(0, 2)
        : [],
    [q.data],
  );
  return (
    <div className="checkpoint">
      <p className="checkpoint-note">
        ลองได้ ข้ามได้ · ใช้คำถามจากชุดฝึกเดิม · ผลนี้ไม่รวมกับแบบฝึกหัดประจำบท
      </p>
      <DataState
        loading={q.isPending}
        error={q.error}
        retry={() => void q.refetch()}
      />
      {q.data && (
        <PracticeRound questions={questions} slug={slug} variant="checkpoint" />
      )}
    </div>
  );
}

function FullStage({
  stage,
  lesson,
  current,
  onGuided,
}: {
  stage: LessonStage;
  lesson: LessonDetail;
  current: boolean;
  onGuided: () => void;
}) {
  return (
    <section
      className="full-stage"
      id={`review-${stage.id}`}
      data-full-stage={stage.id}
      aria-labelledby={`full-title-${stage.id}`}
    >
      <div className="full-stage-title">
        <div>
          <span className="eyebrow">
            {phases.find((p) => p.id === stage.phase)?.label}
          </span>
          <h2 id={`full-title-${stage.id}`} tabIndex={-1}>
            {stage.title}
          </h2>
        </div>
        <button className="text-link" onClick={onGuided}>
          <Play size={16} />
          เรียนช่วงนี้
        </button>
      </div>
      {stage.cards.length ? (
        <>
          <div className="compact-kanji-list">
            {stage.cards.map((c) => (
              <article
                key={c.character}
                data-card-summary={c.character}
                className="compact-kanji"
              >
                <span className="compact-glyph" lang="ja">
                  {c.character}
                </span>
                <div>
                  <strong>{c.meaning_th}</strong>
                  <small>
                    {c.study?.reading.label_th || "คำอ่านตัวอย่าง"}
                    {c.study?.role === "supplementary" && " · เลือกเรียนได้"}
                  </small>
                  {c.study?.reading.kind === "component" ? (
                    <span className="lesson-audio-line">
                      <span lang="ja">{c.study.reading.reading}</span>
                      <LessonAudioButton
                        kind="component"
                        text={c.study.reading.form}
                        reading={c.study.reading.reading}
                      />
                    </span>
                  ) : (
                    <Reading
                      text={c.study?.reading.form || c.character}
                      reading={c.study?.reading.reading || c.reading_example}
                      audioKind={c.study?.reading.kind === "word" ? "word" : "kanji"}
                    />
                  )}
                </div>
              </article>
            ))}
          </div>
          <Disclosure label="เปิดภาพช่วยจำและตัวอย่างของกลุ่มนี้" initialOpen={current}>
            <LessonSections
              sections={stage.sections}
              kanjis={lesson.kanjis}
              slug={lesson.slug}
              showToc={false}
              allowDetails={!!lesson.private_development}
            />
          </Disclosure>
        </>
      ) : stage.phase === "check" ? (
        <p>
          ลองเลือกคำตอบสั้น ๆ ได้ในโหมดเรียนเป็นช่วง ข้ามได้เสมอ และไม่เปลี่ยนชุดข้อสอบประจำบท
        </p>
      ) : (
        <LessonSections
          sections={stage.sections}
          kanjis={lesson.kanjis}
          slug={lesson.slug}
          showToc={false}
          allowDetails={!!lesson.private_development}
        />
      )}
      {!stage.sections.length && stage.phase !== "check" && (
        <p>{stage.focus}</p>
      )}
    </section>
  );
}

export function LessonExperience({
  lesson,
  catalog,
}: {
  lesson: LessonDetail;
  catalog: LessonMetadata[];
}) {
  const stages = useMemo(() => deriveStages(lesson), [lesson]);
  const saved = useRef(readPosition(lesson.slug)).current;
  const [params] = useSearchParams(),
    location = useLocation(),
    navigate = useNavigate(),
    reduce = useReducedMotion();
  const navigationType = useNavigationType();
  const legacy = location.hash.match(/^#lesson-section-(\d+)$/);
  const legacyStage = legacy
    ? stages.find((s) => s.sourceSections.includes(Number(legacy[1])))
    : undefined;
  const mode =
    params.get("mode") === "full"
      ? "full"
      : params.get("mode") === "guided"
        ? "guided"
        : legacy
          ? "full"
          : saved?.mode || "guided";
  const stage = resolveStage(
    stages,
    params.get("stage") || legacyStage?.id || saved?.stage || null,
  );
  const index = stages.indexOf(stage),
    phaseIndex = phases.findIndex((p) => p.id === stage.phase);
  const cardPositions = useRef<Record<string, number>>({
    ...(saved?.card !== undefined ? { [saved.stage]: saved.card } : {}),
  });
  const rawCard = params.get("card"),
    cardIndex = Math.max(
      0,
      Math.min(
        stage.cards.length - 1,
        Number(
          rawCard === null ? cardPositions.current[stage.id] || 0 : rawCard,
        ) || 0,
      ),
    );
  cardPositions.current[stage.id] = cardIndex;
  const [allCards, setAllCards] = useState<Record<string, boolean>>({});
  const [visited, setVisited] = useState<string[]>(
    () => saved?.visited.filter((id) => stages.some((s) => s.id === id)) || [],
  );
  const [outlineOpen, setOutlineOpen] = useState(false);
  const outlineTrigger = useRef<HTMLElement | null>(null);
  const toggleOutline = (button: HTMLElement) => {
    outlineTrigger.current = button;
    setOutlineOpen(!outlineOpen);
    if (!outlineOpen)
      requestAnimationFrame(() =>
        document
          .getElementById("chapter-outline")
          ?.scrollIntoView({ block: "start", behavior: "auto" }),
      );
  };
  const [direction, setDirection] = useState(1);
  useEffect(() => {
    if (!outlineOpen) return;
    const close = (event: PointerEvent) => {
      if (
        event.target instanceof Element &&
        !event.target.closest(
          ".chapter-outline,.outline-toggle-row,.action-outline",
        )
      )
        setOutlineOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [outlineOpen]);
  const frame = useRef<HTMLDivElement>(null),
    heading = useRef<HTMLHeadingElement>(null);
  const pending = useRef(true),
    pauseScroll = useRef(0),
    currentId = useRef(stage.id);
  const pathname = `/lessons/${lesson.slug}`;
  const href = (id: string, view = mode) =>
    `${pathname}?mode=${view}&stage=${id}${cardPositions.current[id] ? `&card=${cardPositions.current[id]}` : ""}${view === "full" ? `#review-${id}` : ""}`;
  const returnTo = href(stage.id);
  const groups = useQuery({
    queryKey: ["comparison-groups"],
    queryFn: () => api<ComparisonGroup[]>("/learning/comparison-groups"),
  });
  const chapterGroups =
    groups.data?.filter((g) => g.slug === lesson.slug) || [];
  const counts = {
    cards: stages.reduce((n, s) => n + s.cards.length, 0),
    words: stages.reduce(
      (n, s) =>
        n +
        s.sections.reduce(
          (n, t) =>
            n + t.blocks.reduce((n, b) => n + (b.vocabulary?.length || 0), 0),
          0,
        ),
      0,
    ),
    sentences: stages.reduce(
      (n, s) =>
        n +
        s.sections.reduce(
          (n, t) =>
            n + t.blocks.reduce((n, b) => n + (b.sentences?.length || 0), 0),
          0,
        ),
      0,
    ),
  };
  const go = useCallback(
    (
      id: string,
      view: "guided" | "full" = mode,
      replace = false,
      scroll = true,
    ) => {
      const next = resolveStage(stages, id);
      setDirection(
        stages.indexOf(next) >=
          stages.findIndex((s) => s.id === currentId.current)
          ? 1
          : -1,
      );
      pending.current = scroll;
      if (scroll) pauseScroll.current = Date.now() + 450;
      currentId.current = next.id;
      setOutlineOpen(false);
      navigate(
        `${pathname}?mode=${view}&stage=${next.id}${cardPositions.current[next.id] ? `&card=${cardPositions.current[next.id]}` : ""}${view === "full" ? `#review-${next.id}` : ""}`,
        { replace, preventScrollReset: true },
      );
    },
    [mode, navigate, pathname, stages],
  );
  useEffect(() => {
    currentId.current = stage.id;
    setVisited((previous) =>
      previous.includes(stage.id) ? previous : [...previous, stage.id],
    );
    if (
      params.get("mode") !== mode ||
      params.get("stage") !== stage.id ||
      legacy
    ) {
      navigate(href(stage.id), { replace: true, preventScrollReset: true });
    }
  }, [stage.id, mode, params, legacy?.[0], pathname, navigate]);
  useEffect(() => {
    writePosition(lesson.slug, {
      mode,
      stage: stage.id,
      visited,
      card: cardIndex,
    });
  }, [lesson.slug, mode, stage.id, visited, cardIndex]);
  useEffect(() => {
    if (!pending.current && mode !== "guided" && navigationType !== "POP")
      return;
    pending.current = false;
    pauseScroll.current = Date.now() + 450;
    const timer = window.setTimeout(
      () => {
        if (mode === "full") {
          const node = document.getElementById(`review-${stage.id}`);
          node?.scrollIntoView({ block: "start", behavior: "auto" });
          node
            ?.querySelector<HTMLElement>("h2")
            ?.focus({ preventScroll: true });
        } else if (stage.id !== "discover") {
          frame.current?.scrollIntoView({ block: "start", behavior: "auto" });
          heading.current?.focus({ preventScroll: true });
        }
      },
      reduce ? 0 : 220,
    );
    return () => window.clearTimeout(timer);
  }, [mode, stage.id, reduce]);
  useEffect(() => {
    if (mode !== "full") return;
    let timer = 0;
    const track = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        if (Date.now() < pauseScroll.current) return;
        const nodes = [
          ...document.querySelectorAll<HTMLElement>("[data-full-stage]"),
        ];
        const visible = nodes
          .filter((n) => n.getBoundingClientRect().top <= 190)
          .at(-1);
        const id = visible?.dataset.fullStage;
        if (id && id !== currentId.current) go(id, "full", true, false);
      }, 160);
    };
    window.addEventListener("scroll", track, { passive: true });
    return () => {
      window.removeEventListener("scroll", track);
      window.clearTimeout(timer);
    };
  }, [mode, go]);
  const activePhases = phases.filter((p) =>
    stages.some((s) => s.phase === p.id),
  );
  const currentCatalog = catalog.findIndex((l) => l.slug === lesson.slug),
    next = catalog[currentCatalog + 1];
  const onMode = (value: string) => {
    const view = value === "full" ? "full" : "guided";
    if (view === mode) return;
    const nodes = [
      ...document.querySelectorAll<HTMLElement>("[data-full-stage]"),
    ].filter((n) => n.getBoundingClientRect().height > 0);
    const visible =
      nodes.filter((n) => n.getBoundingClientRect().top <= 190).at(-1) ||
      nodes[0];
    go(
      mode === "full" && Date.now() >= pauseScroll.current
        ? visible?.dataset.fullStage || stage.id
        : stage.id,
      view,
    );
  };
  const quizHref = withLessonReturn(`/quiz/${lesson.slug}`, returnTo);
  const content = (
    <LessonReturnContext.Provider value={returnTo}>
      <div className={`hybrid-lesson mode-${mode}`}>
        <div className="hybrid-title">
          <div>
            <Link className="text-link" to="/lessons">
              <ArrowLeft size={16} />
              เส้นทางบทเรียน
            </Link>
            <p className="eyebrow">
              บทที่ {String(lesson.chapter || 2).padStart(2, "0")} ·{" "}
              {counts.cards} ตัวอักษร
            </p>
            <h1>
              {lesson.title_th}
              <span className="coral">。</span>
            </h1>
          </div>
          <ChoicePicker
            label="เลือกบทเรียน"
            triggerLabel={`เปลี่ยนบท · ${lesson.chapter || 2}`}
            value={lesson.slug}
            options={catalog.map((l) => ({
              value: l.slug,
              label: `บท ${l.chapter} · ${l.title_th}`,
            }))}
            onChange={(slug) => navigate(`/lessons/${slug}`)}
          />
        </div>
        <div className="lesson-mode-row">
          <SegmentedControl
            label="รูปแบบบทเรียน"
            value={mode}
            options={[
              { value: "guided", label: "เรียนเป็นช่วง" },
              { value: "full", label: "ดูบทเรียนทั้งหมด" },
            ]}
            onChange={onMode}
          />
          <Link className="text-link" to={quizHref}>
            ไปแบบฝึกหัดได้ทันที
            <ArrowRight size={16} />
          </Link>
          {(mode === "full" || stage.phase === "review") && (
            <LessonSaveProgress slug={lesson.slug} />
          )}
        </div>
        <div className="phase-rail" aria-label="เส้นทางเรียนรู้ในบท">
          {activePhases.map((p, i) => {
            const steps = stages.filter((s) => s.phase === p.id),
              seen = steps.every((s) => visited.includes(s.id));
            return (
              <button
                key={p.id}
                aria-current={stage.phase === p.id ? "step" : undefined}
                onClick={() => go(steps[0].id)}
              >
                <span className="phase-marker">
                  {seen ? <Check size={17} /> : i + 1}
                </span>
                <span>
                  <strong>{p.label}</strong>
                  <small>
                    {stage.phase === p.id
                      ? "กำลังอยู่ช่วงนี้"
                      : seen
                        ? "เคยเปิดแล้ว"
                        : p.hint}
                  </small>
                </span>
              </button>
            );
          })}
        </div>
        <div className="journey-progress">
          <span>
            ตำแหน่ง {index + 1} / {stages.length} · {phases[phaseIndex].label}
          </span>
          <span>เคยเปิด {visited.length} ช่วง · เฉพาะแท็บนี้</span>
          <div
            role="progressbar"
            aria-label="ตำแหน่งในบทเรียน"
            aria-valuemin={1}
            aria-valuemax={stages.length}
            aria-valuenow={index + 1}
          >
            <m.span
              animate={{ width: `${((index + 1) / stages.length) * 100}%` }}
              transition={{ duration: reduce ? 0 : 0.18 }}
            />
          </div>
        </div>
        <div className="outline-toggle-row">
          <button
            id="outline-toggle"
            onClick={(event) => toggleOutline(event.currentTarget)}
            aria-expanded={outlineOpen}
            aria-controls="chapter-outline"
          >
            <List size={18} />
            สารบัญและข้ามไปยังช่วงเรียน
          </button>
        </div>
        <div className="lesson-workspace">
          <aside
            className={`chapter-outline ${outlineOpen ? "is-open" : ""}`}
            id="chapter-outline"
            aria-label="สารบัญบทเรียน"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setOutlineOpen(false);
                outlineTrigger.current?.focus();
              }
            }}
          >
            <p className="eyebrow">เลือกจังหวะของคุณ</p>
            <ol>
              {stages.map((s, i) => (
                <li key={s.id}>
                  <button
                    data-stage-target={s.id}
                    aria-current={s.id === stage.id ? "step" : undefined}
                    onClick={() => go(s.id)}
                  >
                    <span>
                      {visited.includes(s.id) ? (
                        <Check size={16} />
                      ) : (
                        String(i + 1).padStart(2, "0")
                      )}
                    </span>
                    <span>
                      {s.title}
                      <small>
                        {s.id === stage.id
                          ? "ตำแหน่งปัจจุบัน"
                          : visited.includes(s.id)
                            ? "เคยเปิดแล้ว"
                            : "เปิดดูได้ทันที"}
                      </small>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
            <p className="subtle">
              บอกช่วงที่เคยเปิด ไม่ใช่คะแนนหรือการบันทึกความสำเร็จในบัญชี
            </p>
          </aside>
          <div className="lesson-dominant-surface" ref={frame}>
            {mode === "guided" ? (
              <>
                <AnimatePresence mode="wait" initial={false}>
                  <m.section
                    key={stage.id}
                    className={`guided-stage stage-${stage.phase}`}
                    data-stage={stage.id}
                    initial={{
                      opacity: reduce ? 1 : 0.6,
                      x: reduce ? 0 : direction * 12,
                    }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{
                      opacity: reduce ? 1 : 0,
                      x: reduce ? 0 : -direction * 8,
                    }}
                    transition={{ duration: reduce ? 0 : 0.18 }}
                  >
                    <div className="stage-heading">
                      <span className="icon-tile">
                        {stage.phase === "connect" ? (
                          <GitCompareArrows size={22} />
                        ) : stage.phase === "review" ? (
                          <RotateCcw size={22} />
                        ) : (
                          <Compass size={22} />
                        )}
                      </span>
                      <div>
                        <p className="eyebrow">
                          {phases.find((p) => p.id === stage.phase)?.label} ·
                          ช่วง {index + 1} จาก {stages.length}
                        </p>
                        <h2 ref={heading} tabIndex={-1}>
                          {stage.title}
                        </h2>
                      </div>
                    </div>
                    {stage.phase === "discover" ? (
                      <>
                        {!stage.sections.length && (
                          <p className="stage-focus">{stage.focus}</p>
                        )}
                        <LessonSections
                          sections={stage.sections}
                          kanjis={lesson.kanjis}
                          slug={lesson.slug}
                          showToc={false}
                          allowDetails={!!lesson.private_development}
                        />
                        <div
                          className="discovery-glyphs"
                          lang="ja"
                          aria-hidden="true"
                        >
                          {lesson.anchors.slice(0, 4).map((c) => (
                            <span key={c}>
                              {c}
                            </span>
                          ))}
                        </div>
                        <div className="discovery-facts">
                          <span>
                            <BookOpen size={18} />
                            {counts.cards} ตัวอักษร ·{" "}
                            {stages.filter((s) => s.cards.length).length} กลุ่มเล็ก
                          </span>
                          <span>
                            {counts.words} คำศัพท์
                            {counts.sentences
                              ? ` · ${counts.sentences} ประโยคตัวอย่าง`
                              : ""}
                          </span>
                          {chapterGroups.length > 0 && (
                            <span>{chapterGroups.length} ชุดเปรียบเทียบ</span>
                          )}
                        </div>
                        <p className="session-caption">
                          ตำแหน่งเรียนจำไว้เฉพาะแท็บนี้ · เริ่มฝึกได้โดยไม่ต้องเรียนครบทุกช่วง
                        </p>
                        <div className="hero-actions discovery-actions">
                          <button
                            className="primary"
                            onClick={() =>
                              go(
                                [...visited]
                                  .reverse()
                                  .find((id) => id !== "discover") ||
                                  stages[1]?.id ||
                                  "review",
                              )
                            }
                          >
                            <Play size={16} aria-hidden="true" />
                            {visited.some((id) => id !== "discover")
                              ? "เรียนต่อ"
                              : "เริ่มเรียน"}
                          </button>
                          <button onClick={() => go(stage.id, "full")}>
                            เปิดบทเรียนฉบับเต็ม
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        {stage.phase !== "check" && (
                          <p className="stage-focus">{stage.focus}</p>
                        )}
                        {stage.cards.length > 0 && (
                          <div className="mobile-kanji-picker">
                            <p>เลือกดูทีละตัว หรือเปิดดูพร้อมกันทั้งกลุ่ม</p>
                            <div
                              role="group"
                              aria-label="ตัวอักษรในกลุ่มนี้"
                              style={{
                                gridTemplateColumns: `repeat(${stage.cards.length},minmax(0,1fr))`,
                              }}
                            >
                              {stage.cards.map((c, i) => (
                                <button
                                  key={c.character}
                                  aria-label={`ดู ${c.character}`}
                                  aria-pressed={cardIndex === i}
                                  onClick={() => {
                                    cardPositions.current[stage.id] = i;
                                    navigate(
                                      `${pathname}?mode=guided&stage=${stage.id}&card=${i}`,
                                      {
                                        replace: true,
                                        preventScrollReset: true,
                                      },
                                    );
                                  }}
                                >
                                  <span lang="ja">{c.character}</span>
                                  {cardIndex === i && <Check size={14} />}
                                  <small>
                                    {c.study?.role === "supplementary"
                                      ? "เลือกเรียนได้"
                                      : i + 1}
                                  </small>
                                </button>
                              ))}
                            </div>
                            <button
                              className="text-link"
                              aria-pressed={!!allCards[stage.id]}
                              onClick={() =>
                                setAllCards((p) => ({
                                  ...p,
                                  [stage.id]: !p[stage.id],
                                }))
                              }
                            >
                              {allCards[stage.id]
                                ? "กลับไปดูทีละตัว"
                                : "ดูทั้งกลุ่มพร้อมกัน"}
                            </button>
                          </div>
                        )}
                        {stage.phase !== "check" && (
                          <LessonSections
                            sections={stage.sections}
                            kanjis={lesson.kanjis}
                            slug={lesson.slug}
                            showToc={false}
                            allowDetails={!!lesson.private_development}
                            focused={stage.phase === "learn"}
                            activeCharacter={stage.cards[cardIndex]?.character}
                            showAllCards={!!allCards[stage.id]}
                          />
                        )}
                        {stage.cards.length > 0 && (
                          <button
                            className="text-link"
                            onClick={() => go(stage.id, "full")}
                          >
                            <List size={17} />
                            ดูทุกกลุ่มและรายละเอียดในบท
                          </button>
                        )}
                        {stage.cards.length > 0 &&
                          chapterGroups.some((g) =>
                            g.characters.every((c) =>
                              stage.cards.some(
                                (card) => card.character === c.character,
                              ),
                            ),
                          ) && (
                            <div className="related-learning-pairs">
                              <h3>ลองเทียบคู่ที่อยู่ในกลุ่มนี้</h3>
                              {chapterGroups
                                .filter((g) =>
                                  g.characters.every((c) =>
                                    stage.cards.some(
                                      (card) => card.character === c.character,
                                    ),
                                  ),
                                )
                                .map((g) => (
                                  <Link
                                    key={g.id}
                                    className="comparison-tile"
                                    to={withLessonReturn(
                                      `/compare?group=${g.id}`,
                                      returnTo,
                                    )}
                                  >
                                    <GitCompareArrows size={17} />
                                    <span lang="ja">{g.title}</span>
                                    <ArrowRight size={17} />
                                  </Link>
                                ))}
                            </div>
                          )}
                        {stage.phase === "connect" &&
                          chapterGroups.length > 0 && (
                            <div className="guided-comparison-links">
                              <h3>เลือกคู่เพื่อเปิดตารางแบบโต้ตอบ</h3>
                              {chapterGroups.map((g) => (
                                <Link
                                  className="comparison-tile"
                                  key={g.id}
                                  to={withLessonReturn(
                                    `/compare?group=${g.id}`,
                                    returnTo,
                                  )}
                                >
                                  <span lang="ja">{g.title}</span>
                                  <ArrowRight size={16} />
                                </Link>
                              ))}
                            </div>
                          )}
                        {stage.phase === "review" && (
                          <div className="chapter-recap">
                            <div className="recap-glyphs" lang="ja">
                              {lesson.kanjis.map((k) => (
                                <span key={k.character}>{k.character}</span>
                              ))}
                            </div>
                            <p>
                              เลือกย้อนดูช่วงที่ยังสับสน หรือไปลองแบบฝึกหัดประจำบท
                              ผลแบบฝึกหัดบอกผลรอบนั้น ไม่ใช่การยืนยันว่าเรียนครบทุกช่วง
                            </p>
                            <div className="hero-actions">
                              <button
                                onClick={() =>
                                  go(
                                    stages.find((s) => s.cards.length)?.id ||
                                      "discover",
                                  )
                                }
                              >
                                <RotateCcw size={17} />
                                กลับไปทวนกลุ่มตัวอักษร
                              </button>
                              <Link className="button primary" to={quizHref}>
                                เริ่มแบบฝึกหัดประจำบท
                                <ArrowRight size={17} />
                              </Link>
                            </div>
                            {next && (
                              <Link
                                className="text-link"
                                to={`/lessons/${next.slug}`}
                              >
                                ดูบทถัดไป · {next.title_th}
                                <ArrowRight size={16} />
                              </Link>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </m.section>
                </AnimatePresence>
              </>
            ) : (
              <div className="full-lesson">
                <div className="full-mode-heading">
                  <h2>บทเรียนทั้งหมด · เลือกทวนได้ตามจังหวะ</h2>
                  <p>
                    แถวสรุปแสดงรูป คำอ่าน และความหมาย
                    เปิดรายละเอียดเพื่อดูภาพจำและตัวอย่างครบทุกกลุ่ม
                  </p>
                </div>
                {stages.map((s) => (
                  <FullStage
                    key={s.id}
                    stage={s}
                    lesson={lesson}
                    current={s.id === stage.id}
                    onGuided={() => go(s.id, "guided")}
                  />
                ))}
              </div>
            )}
            {/* Keep the optional checkpoint mounted when switching modes/stages. */}
            <div hidden={mode !== "guided" || stage.phase !== "check"}>
              <QuickCheck
                slug={lesson.slug}
                active={mode === "guided" && stage.phase === "check"}
              />
            </div>
          </div>
        </div>
        <nav className="learning-actions" aria-label="นำทางช่วงเรียน">
          <button
            className="review-mode-switch"
            onClick={() => onMode(mode === "guided" ? "full" : "guided")}
          >
            <BookOpen size={17} />
            {mode === "guided" ? "ทวนทั้งบท" : "กลับไปเรียนเป็นช่วง"}
          </button>
          <button
            className="action-outline"
            aria-expanded={outlineOpen}
            aria-controls="chapter-outline"
            onClick={(event) => toggleOutline(event.currentTarget)}
          >
            <List size={17} />
            สารบัญ
          </button>
          <button
            disabled={index === 0}
            onClick={() => go(stages[index - 1].id)}
          >
            <ArrowLeft size={18} />
            ก่อนหน้า
          </button>
          <span>
            {index + 1} / {stages.length}
          </span>
          {index < stages.length - 1 ? (
            <button
              className="primary"
              onClick={() => go(stages[index + 1].id)}
            >
              {stage.phase === "check"
                ? "ข้าม / ไปทวนต่อ"
                : `ถัดไป: ${phases.find((p) => p.id === stages[index + 1].phase)?.label}`}
              <ArrowRight size={18} />
            </button>
          ) : (
            <Link className="button primary" to={quizHref}>
              เริ่มฝึก
              <ArrowRight size={18} />
            </Link>
          )}
        </nav>
      </div>
    </LessonReturnContext.Provider>
  );
  return (
    <LessonAudio
      slug={lesson.slug}
      enabled={
        lesson.status === "published" &&
        !lesson.private_development
      }
      quizOnly={mode === "guided" && stage.phase === "check"}
      playbackScope={mode === "full" ? "full" : `${mode}:${stage.id}:${cardIndex}`}
    >
      {content}
    </LessonAudio>
  );
}
