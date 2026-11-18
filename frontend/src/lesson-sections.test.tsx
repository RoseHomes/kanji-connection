import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LessonSections } from "./lesson-sections";
import { KanjiCard } from "./components";
import type { Kanji, SourceCard } from "./types";
afterEach(cleanup);
const shared: Kanji = {
  character: "口",
  meaning_th: "shared first candidate",
  onyomi: [],
  kunyomi: ["くち"],
  romaji: "",
  strokes: 3,
  component: "",
  note_th: "",
  source_url: "",
  review_status: "needs_review",
};
const occurrence: SourceCard = {
  character: "口",
  meaning_th: "lesson-specific source gloss",
  reading_example: "ぐち",
  example: "入口 いりぐち",
  memory_note: "source note",
  pdf_page: 60,
};
it("renders the lesson-specific source gloss rather than a shared first candidate", () => {
  render(<KanjiCard item={shared} source={occurrence} />);
  expect(screen.getByText("lesson-specific source gloss")).toBeVisible();
  expect(screen.queryByText("shared first candidate")).not.toBeInTheDocument();
});
it("keeps a contextual reading segment out of standalone character furigana", () => {
  const { container } = render(
    <KanjiCard
      item={shared}
      source={{
        ...occurrence,
        editorial_reading_scope: {
          source_reading: "ぐち",
          effective_reading: "くち",
          scope: "compound_voicing",
          context_forms: ["入口", "出口"],
          note: "Existing editorial scope note",
        },
      }}
    />,
  );
  expect(container.querySelector(".card-example ruby")).toBeNull();
  expect(screen.getByText(/คำอ่านตามแหล่งข้อมูล/)).toHaveTextContent("ぐち");
  expect(screen.getByText(/ดัชนีคำอ่านแยก/)).toHaveTextContent("くち");
  expect(screen.getByText("หมายเหตุคำอ่านตามบริบท")).toBeVisible();
});
it("renders source group-ruby, Thai vocabulary and PDF provenance", () => {
  const { container } = render(
    <MemoryRouter>
      <LessonSections
        slug="chapter-02"
        kanjis={[]}
        sections={[
          {
            kind: "vocabulary",
            pdf_pages: [23],
            blocks: [
              {
                vocabulary: [
                  {
                    word: "木",
                    reading: "き",
                    meaning_th: "ต้นไม้",
                    pdf_page: 23,
                  },
                ],
              },
            ],
          },
        ]}
      />
    </MemoryRouter>,
  );
  expect(container.querySelector("ruby[lang=ja] rt")).toHaveTextContent("き");
  expect(screen.getByText("ต้นไม้")).toBeVisible();
  expect(screen.getAllByText("PDF หน้า 23")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "คำศัพท์" })).toHaveAttribute(
    "href",
    "#lesson-section-0",
  );
});
it("preserves a missing mnemonic core and presents existing source pairs only", () => {
  const { container } = render(
    <MemoryRouter>
      <LessonSections
        slug="chapter-02"
        kanjis={[]}
        sections={[
          {
            kind: "mnemonic",
            pdf_pages: [22],
            blocks: [
              {
                diagram: {
                  core: null,
                  related: [],
                  comparison_pairs: [
                    [
                      { kanji: "木", reading: "き", meaning_th: "ต้นไม้" },
                      { kanji: "本", reading: "ほん", meaning_th: "หนังสือ" },
                    ],
                  ],
                },
              },
            ],
          },
        ]}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText(/แหล่งข้อมูลไม่ระบุแกนกลาง/)).toBeVisible();
  expect(container.querySelectorAll(".comparison-pair")).toHaveLength(1);
  expect(container.querySelector(".network-arrow")).toBeNull();
  expect(screen.getByText(/ยังไม่ยืนยันว่าเป็นประวัติที่มาของอักษร/)).toBeVisible();
});
it("labels typed component endpoints and links exercises to the actual chapter", () => {
  render(
    <MemoryRouter>
      <LessonSections
        slug="chapter-16"
        kanjis={[]}
        sections={[
          {
            kind: "comparison",
            pdf_pages: [118],
            blocks: [
              {
                pairs: [[{ kanji: "氵" }, { kanji: "水" }]],
                typed_comparisons: [
                  {
                    endpoints: [
                      { kind: "component", glyph: "氵" },
                      { kind: "kanji", glyph: "水" },
                    ],
                  },
                ],
              },
            ],
          },
          {
            kind: "exercises",
            pdf_pages: [122],
            blocks: [
              {
                exercises: [
                  {
                    number: 1,
                    prompt: "source question",
                    pdf_page: 122,
                    type: "reading",
                  },
                ],
              },
            ],
          },
        ]}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText("ส่วนประกอบ")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "เปิดแบบฝึกหัดแบบโต้ตอบ" }),
  ).toHaveAttribute("href", "/quiz/chapter-16");
});
