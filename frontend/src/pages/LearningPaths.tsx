import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, Check } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { DataState, EmptyState, Reading } from "../components";
import { LessonExperience } from "../lesson-experience";
import { Chips, PageHeading } from "../ui";
import {
  pathInfo,
  unitLesson,
  type ItemPage,
  type LearningPath,
  type LearningUnit,
  type PathDetail,
  type PathKind,
} from "../learning-paths";

const levels = [5, 4, 3, 2, 1];
const itemTypes = [
  { value: "all", label: "ทั้งหมด" },
  { value: "kanji", label: "คันจิ" },
  { value: "vocabulary", label: "คำศัพท์" },
  { value: "sentence", label: "ประโยค" },
];
const pathsApi = "/learning/paths";

function CountText({ path }: { path: LearningPath }) {
  const { kanji, vocabulary, sentence } = path.counts;
  return (
    <>
      {kanji} คันจิ · {vocabulary} คำศัพท์{sentence ? ` · ${sentence} ประโยค` : ""}
    </>
  );
}

export function LearningPathList({ kind }: { kind: PathKind }) {
  const { base, title } = pathInfo[kind];
  const query = useInfiniteQuery({
    queryKey: ["learning-paths", kind],
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      api<LearningPath[]>(
        `${pathsApi}?kind=${kind}&limit=24&offset=${pageParam}`,
        { signal, anonymous: true },
      ),
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === 24 ? pages.length * 24 : undefined,
  });
  const paths = query.data?.pages.flat() || [];
  const entries =
    kind === "jlpt" && query.data
      ? levels.map((level) => {
          const path = paths.find((p) => p.level === level);
          return {
            slug: path?.slug || `n${level}`,
            title: path?.title_th || `JLPT N${level}`,
            path,
          };
        })
      : paths.map((path) => ({ slug: path.slug, title: path.title_th, path }));
  return (
    <div className="page section learning-paths">
      <PageHeading
        eyebrow={kind === "jlpt" ? "JLPT N5–N1" : "LEARN BY TOPIC"}
        title={title}
      >
        {kind === "jlpt" && <p>เลือกฝึกคันจิและคำศัพท์ตามระดับอ้างอิงสำหรับเตรียม JLPT</p>}
      </PageHeading>
      <DataState
        loading={query.isPending}
        error={query.error}
        retry={() => void query.refetch()}
      />
      {query.isSuccess && !entries.length && (
        <EmptyState title="ยังไม่มีหมวดที่เปิดให้เรียน" />
      )}
      <div className="lesson-grid">
        {entries.map(({ slug, title, path }) => (
          <Link className="lesson-card" key={slug} to={`${base}/${slug}`}>
            <h2>
              <span>{title}</span>
              <ArrowUpRight size={18} aria-hidden="true" />
            </h2>
            {path?.summary_th && <p>{path.summary_th}</p>}
            <p className="path-card-count">
              {path && Object.values(path.counts).some(Boolean) ? (
                <CountText path={path} />
              ) : (
                "กำลังเตรียมหน่วยเรียน"
              )}
            </p>
          </Link>
        ))}
      </div>
      {query.hasNextPage && (
        <button
          type="button"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          ดูหมวดเพิ่มเติม
        </button>
      )}
    </div>
  );
}

export function LearningPathPage({ kind }: { kind: PathKind }) {
  const { slug } = useParams();
  const apiPath = `${pathsApi}/${kind}/${encodeURIComponent(slug || "")}`;
  const { base, title } = pathInfo[kind];
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") || "").slice(0, 100);
  const type = itemTypes.some((item) => item.value === params.get("type"))
    ? params.get("type")!
    : "all";
  const include =
    kind === "jlpt" && params.get("include_prerequisites") === "true";
  const sort =
    kind === "jlpt" && params.get("sort") === "reference"
      ? "reference"
      : "learning";
  const path = useQuery({
    queryKey: ["learning-path", kind, slug],
    queryFn: ({ signal }) =>
      api<PathDetail>(apiPath, {
        signal,
        anonymous: true,
      }),
  });
  const items = useInfiniteQuery({
    queryKey: ["learning-path-items", kind, slug, type, q, sort, include],
    initialPageParam: "",
    enabled: !!path.data,
    queryFn: ({ pageParam, signal }) => {
      const search = new URLSearchParams({ q, sort });
      if (type !== "all") search.set("type", type);
      if (include) search.set("include_prerequisites", "true");
      if (pageParam) search.set("cursor", pageParam);
      return api<ItemPage>(`${apiPath}/items?${search}`, {
        signal,
        anonymous: true,
      });
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor || undefined,
  });
  const update = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setParams(next, { replace: true, preventScrollReset: true });
  };
  const level = kind === "jlpt" && /^n[1-5]$/.test(slug || "");
  const preparing =
    level && path.error instanceof ApiError && path.error.status === 404;
  const data = path.data;
  const reference = data?.reference;
  return (
    <div className="page section learning-paths">
      <Link className="text-link path-back" to={base}>
        <ArrowLeft size={17} />
        {title}
      </Link>
      <PageHeading
        eyebrow={title}
        title={
          data?.title_th || (level ? `JLPT ${slug?.toUpperCase()}` : title)
        }
      >
        {data?.summary_th && <p>{data.summary_th}</p>}
        {data && (
          <p className="path-summary-count">
            มีให้เรียน <CountText path={data} />
          </p>
        )}
      </PageHeading>
      <DataState
        loading={path.isPending}
        error={preparing ? null : path.error}
        retry={() => void path.refetch()}
      />
      {preparing && <EmptyState title="กำลังเตรียมหน่วยเรียน" />}
      {reference && (
        <aside className="path-reference">
          <p>
            ชุดข้อมูลอ้างอิงมี {reference.totals.kanji.toLocaleString()} คันจิ และ{" "}
            {reference.totals.vocabulary.toLocaleString()} คำศัพท์{" "}
            ระดับนี้ใช้เป็นแนวทางเตรียมสอบ
          </p>
          <p className="path-reference-meta">
            <a href={reference.source_url}>{reference.attribution}</a>
            {reference.license === "CC BY-SA 4.0" ? (
              <a href="https://creativecommons.org/licenses/by-sa/4.0/">
                {reference.license}
              </a>
            ) : (
              <span>{reference.license}</span>
            )}
            <span>
              รุ่น <code>{reference.version.slice(0, 12)}</code>
            </span>
          </p>
        </aside>
      )}
      {data && (
        <>
          <section className="path-section" aria-labelledby="path-units-title">
            <h2 id="path-units-title">หน่วยเรียน</h2>
            {data.units.length ? (
              <div className="lesson-grid">
                {data.units.map((unit) => (
                  <Link
                    className="lesson-card"
                    key={unit.unit_key}
                    to={`${base}/${data.slug}/units/${unit.unit_key}`}
                  >
                    <h3>
                      <span>{unit.title_th}</span>
                      <ArrowUpRight size={18} aria-hidden="true" />
                    </h3>
                    {unit.intro_th && <p>{unit.intro_th}</p>}
                    <p className="path-card-count">
                      {unit.available_count} รายการ
                    </p>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState title="กำลังเตรียมหน่วยเรียน" />
            )}
          </section>
          <section className="path-section" aria-labelledby="path-items-title">
            <div className="path-section-heading">
              <h2 id="path-items-title">รายการที่เปิดให้เรียน</h2>
              {(data.counts.kanji > 0 || include) && (
                <Link
                  className="text-link"
                  to={`/explore?${new URLSearchParams({
                    [kind]: kind === "jlpt" ? `n${data.level}` : data.slug,
                    ...(include && { include_prerequisites: "true" }),
                  })}`}
                >
                  สำรวจคันจิในเส้นทางนี้ <ArrowUpRight size={16} />
                </Link>
              )}
            </div>
            <div
              className="path-filters"
              role="group"
              aria-label="ตัวกรองรายการเรียน"
            >
              <Chips
                items={itemTypes}
                value={type}
                label="ชนิดเนื้อหา"
                onChange={(value) =>
                  update("type", value === "all" ? "" : value)
                }
              />
              <div className="path-filter-fields">
                <label className="path-field path-field-search">
                  <span>ค้นหาในเส้นทาง</span>
                  <input
                    type="search"
                    value={q}
                    maxLength={100}
                    onChange={(e) => update("q", e.target.value)}
                  />
                </label>
                {kind === "jlpt" && (
                  <>
                    <label className="path-field">
                      <span>เรียงตาม</span>
                      <select
                        value={sort}
                        onChange={(e) =>
                          update(
                            "sort",
                            e.target.value === "learning" ? "" : e.target.value,
                          )
                        }
                      >
                        <option value="learning">ลำดับการเรียน</option>
                        <option value="reference">ลำดับอ้างอิง</option>
                      </select>
                    </label>
                    {data.level !== 5 && (
                      <label className="path-checkbox">
                        <span className="path-checkbox-mark">
                          <input
                            type="checkbox"
                            checked={include}
                            onChange={(e) =>
                              update(
                                "include_prerequisites",
                                e.target.checked ? "true" : "",
                              )
                            }
                          />
                          <Check
                            size={15}
                            strokeWidth={2.5}
                            aria-hidden="true"
                          />
                        </span>
                        <span>รวมระดับพื้นฐานกว่า</span>
                      </label>
                    )}
                  </>
                )}
              </div>
            </div>
            <DataState
              loading={items.isPending}
              error={items.error}
              retry={() => void items.refetch()}
            />
            {items.isSuccess && !items.data.pages[0].total && (
              <EmptyState title="ไม่พบรายการตามตัวกรอง" />
            )}
            {!!items.data?.pages[0].total && (
              <p className="count-label path-result-count" role="status">
                {items.data.pages[0].total} รายการ
              </p>
            )}
            <div className="vocabulary-list path-item-list">
              {items.data?.pages
                .flatMap((page) => page.items)
                .map((item) => (
                  <article
                    className="vocabulary-item"
                    key={`${item.type}:${item.id}`}
                  >
                    {item.type === "kanji" ? (
                      <Link
                        to={`/explore/${encodeURIComponent(item.text)}`}
                        lang="ja"
                      >
                        <Reading
                          text={item.text}
                          reading={
                            item.kanji.onyomi[0] || item.kanji.kunyomi[0] || ""
                          }
                        />
                      </Link>
                    ) : (
                      <Reading text={item.text} reading={item.reading} />
                    )}
                    {item.level && (
                      <span className="count-label">N{item.level}</span>
                    )}
                    <p>{item.meaning_th}</p>
                    {item.context_note_th && <p>{item.context_note_th}</p>}
                    {item.unit_key && (
                      <Link
                        className="text-link"
                        to={`${base}/${item.path_slug}/units/${item.unit_key}`}
                      >
                        เปิดหน่วยเรียน <ArrowUpRight size={15} />
                      </Link>
                    )}
                  </article>
                ))}
            </div>
            {items.hasNextPage && (
              <button
                type="button"
                className="path-load-more"
                disabled={items.isFetchingNextPage}
                onClick={() => void items.fetchNextPage()}
              >
                ดูรายการเพิ่มเติม
              </button>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export function LearningUnitPage({ kind }: { kind: PathKind }) {
  const { slug, unitKey } = useParams();
  const path = `${pathInfo[kind].base}/${slug}`;
  const query = useQuery({
    queryKey: ["learning-unit", kind, slug, unitKey],
    queryFn: ({ signal }) =>
      api<LearningUnit>(
        `${pathsApi}/${kind}/${encodeURIComponent(slug || "")}/units/${encodeURIComponent(unitKey || "")}`,
        {
          signal,
          anonymous: true,
        },
      ),
  });
  const unit = query.data;
  if (!unit)
    return (
      <div className="page section">
        <Link className="text-link" to={path}>
          <ArrowLeft size={17} />
          กลับไปยังเส้นทาง
        </Link>
        <DataState
          loading={query.isPending}
          error={query.error}
          retry={() => void query.refetch()}
        />
      </div>
    );
  const unitHref = (key: string) => `${path}/units/${key}`;
  const lesson = unitLesson(unit);
  return (
    <div className="page section hybrid-page learning-unit-page">
      <LessonExperience
        key={lesson.slug}
        lesson={lesson}
        unit={{
          pathname: unitHref(unit.unit_key),
          backHref: path,
          backLabel: unit.path.title_th,
          previousHref: unit.previous_unit_key
            ? unitHref(unit.previous_unit_key)
            : undefined,
          nextHref: unit.next_unit_key
            ? unitHref(unit.next_unit_key)
            : undefined,
        }}
      />
    </div>
  );
}
