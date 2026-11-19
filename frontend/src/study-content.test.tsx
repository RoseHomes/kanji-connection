import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, it, expect } from "vitest";
import { StudyContent } from "./study-content";
import type { SourceCard } from "./types";

afterEach(cleanup);

const card: SourceCard = {
  character: "好",
  meaning_th: "ชอบ",
  reading_example: "すき",
  example: "好き すき",
  memory_note: "好 มี 女 กับ 子; เชื่อมรูปกับคนที่ชอบ",
  pdf_page: 47,
  study: {
    schema_version: 2,
    role: "core",
    required: true,
    revision_id: "test",
    reading: {
      kind: "word",
      label_th: "คำอ่านทั้งคำ",
      form: "好き",
      reading: "すき",
      note_th: "อ่านรวมคานะท้าย",
    },
    example: {
      word: "好き",
      reading: "すき",
      meaning_th: "ชอบ",
      target_scope: "คำอ่านทั้งคำ",
      role: "core",
      optional: false,
    },
    scope_note_th: "好 เดี่ยวไม่อ่าน すき ทุกคำ",
    mnemonic_note_th: "ภาพช่วยจำ ไม่ใช่นิรุกติศาสตร์",
  },
};

describe("working educational content", () => {
  it("keeps historical editorial questions out of supplementary teaching panels", () => {
    const supplementary = structuredClone(card);
    supplementary.study!.role = "supplementary";
    supplementary.study!.scope_note_th = "รอเลือกบทบาทในการทบทวนต้นฉบับ";
    render(<StudyContent card={supplementary} />);
    expect(screen.queryByText("รอเลือกบทบาทในการทบทวนต้นฉบับ")).toBeNull();
    expect(screen.getByText(card.memory_note)).toBeVisible();
  });
  it("prints the full inflected form under a word-reading label", () => {
    const { container } = render(<StudyContent card={card} />);
    const ruby = container.querySelector(".study-reading ruby")!;
    expect(ruby.firstChild?.textContent).toBe("好き");
    expect(ruby.querySelector("rt")).toHaveTextContent("すき");
    expect(screen.getByText(card.memory_note)).toBeVisible();
    expect(screen.getByText("ภาพช่วยจำ ไม่ใช่นิรุกติศาสตร์")).toBeVisible();
  });
  it("separates optional examples from core vocabulary", () => {
    const optional = structuredClone(card);
    optional.study!.example = {
      word: "金閣寺",
      reading: "きんかくじ",
      meaning_th: "วัดคิงกากุจิ",
      target_scope: "閣=かく",
      role: "proper_name",
      optional: true,
    };
    const { container } = render(<StudyContent card={optional} />);
    expect(screen.getByText("ตัวอย่างชื่อสถานที่ · เลือกเรียนได้")).toBeVisible();
    expect(
      container.querySelector("details.optional-example"),
    ).not.toHaveAttribute("open");
    expect(container.querySelector(".core-example")).toBeNull();
  });
  it("labels component names without assigning their name as ruby", () => {
    const component = structuredClone(card);
    component.study!.role = "component";
    component.study!.reading = {
      kind: "component",
      label_th: "ชื่อส่วนประกอบ",
      form: "禾",
      reading: "のぎへん",
      note_th: "ธัญพืช",
    };
    component.study!.example = null;
    const { container } = render(<StudyContent card={component} />);
    expect(screen.getByText("ชื่อส่วนประกอบ")).toBeVisible();
    expect(screen.getByText("のぎへん")).toBeVisible();
    expect(container.querySelector(".study-reading ruby")).toBeNull();
  });
});
