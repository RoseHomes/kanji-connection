import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MotionConfig } from "motion/react";
import { PracticeRound } from "./Quiz";
import type { PracticeQuestion } from "../presentation-types";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
const questions: PracticeQuestion[] = [
  {
    id: "q1",
    kind: "meaning",
    prompt: "木 หมายถึงอะไร?",
    options: [
      { id: "a", text: "ต้นไม้" },
      { id: "b", text: "ป่า" },
      { id: "c", text: "น้ำ" },
    ],
  },
  {
    id: "q2",
    kind: "shape",
    prompt: "จุดต่างของ 木 และ 林 คืออะไร?",
    options: [
      { id: "d", text: "ต้นไม้หนึ่งต้นและสองต้น" },
      { id: "e", text: "เหมือนกัน" },
      { id: "f", text: "มีแต่คำอ่านต่าง" },
    ],
  },
];
const response = (correct: boolean, second = false) => ({
  correct,
  correct_option_id: second ? "d" : "a",
  correct_text: second ? "ต้นไม้หนึ่งต้นและสองต้น" : "ต้นไม้",
  explanation: second ? "林 มี 木 สองตัว" : "木 เป็นรูปต้นไม้",
  selection_explanation: "สังเกตรูปและความหมาย",
  persisted: false,
});
const mount = (qs = questions) =>
  render(
    <MotionConfig reducedMotion="always">
      <MemoryRouter>
        <PracticeRound questions={qs} slug="chapter-02" />
      </MemoryRouter>
    </MotionConfig>,
  );
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  localStorage.clear();
});
it("requires a radio selection, submits only an option ID and shows explicit feedback", async () => {
  mocks.api.mockResolvedValue(response(true));
  mount();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /ตรวจคำตอบ/ })).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  expect(mocks.api).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
  expect(mocks.api.mock.calls[0]).toEqual([
    "/learning/practice/chapter-02/q1/check",
    { method: "POST", body: JSON.stringify({ option_id: "a" }) },
  ]);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
  expect(localStorage.length).toBe(0);
});
it("completes a full round, reviews explanations, and retries only incorrect items", async () => {
  mocks.api
    .mockResolvedValueOnce(response(false))
    .mockResolvedValueOnce(response(true, true))
    .mockResolvedValue(response(true));
  mount();
  fireEvent.click(screen.getByRole("radio", { name: /ป่า/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByText(/อีกนิดเดียว/);
  fireEvent.click(screen.getByRole("button", { name: /ข้อต่อไป/ }));
  await screen.findByText(questions[1].prompt);
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้หนึ่งต้น/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
  fireEvent.click(screen.getByRole("button", { name: /ดูผลการฝึก/ }));
  await screen.findByText("เก่งขึ้นอีกหนึ่งความเชื่อมโยง");
  expect(screen.getByText(/ตอบถูก 1 ข้อ/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /ดูคำตอบทั้งรอบ/ }));
  expect(screen.getByText("林 มี 木 สองตัว")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /ลองข้อที่ยังสับสน/ }));
  expect(screen.getByText("ข้อ 1 จาก 1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
});
it("retries network failures with the same choice and prevents duplicate checks", async () => {
  mocks.api
    .mockRejectedValueOnce(new Error("Try again"))
    .mockResolvedValue(response(true));
  mount(questions.slice(0, 1));
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await waitFor(() => expect(mocks.api).toHaveBeenCalledTimes(2));
  expect(mocks.api.mock.calls[0]).toEqual(mocks.api.mock.calls[1]);
});
it("shows an honest empty state", () => {
  mount([]);
  expect(screen.getByText("บทนี้ยังไม่มีชุดคำถามที่พร้อมเรียน")).toBeInTheDocument();
});
