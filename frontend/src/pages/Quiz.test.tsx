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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PracticeRound } from "./Quiz";
import type { PracticeQuestion } from "../presentation-types";
const mocks = vi.hoisted(() => ({ api: vi.fn(), ownerId: "" }));
vi.mock("../api", () => ({ api: mocks.api }));
vi.mock("../auth", () => ({
  useAuth: () => ({
    session: mocks.ownerId ? { user: { id: mocks.ownerId } } : null,
  }),
}));
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
const preloaded = [{
  ...questions[0],
  feedback: {
    correct_option_id: "a",
    correct_text: "ต้นไม้",
    explanation: "木 เป็นรูปต้นไม้",
    selection_explanations: { correct: "สังเกตรูปได้ถูกต้อง", incorrect: "ลองดูรูปอีกครั้ง" },
  },
}];
const mount = (qs = questions, variant: "quiz" | "checkpoint" = "quiz") =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MotionConfig reducedMotion="always">
        <MemoryRouter>
          <PracticeRound questions={qs} slug="chapter-02" variant={variant} />
        </MemoryRouter>
      </MotionConfig>
    </QueryClientProvider>,
  );
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  mocks.ownerId = "";
  localStorage.clear();
});
it("saves authenticated quiz attempts and reuses the submission ID after a failed response", async () => {
  mocks.ownerId = "reader-a";
  mocks.api
    .mockResolvedValueOnce({ account_writes_enabled: true })
    .mockRejectedValueOnce(new Error("Network error"))
    .mockResolvedValueOnce({ ...response(true), persisted: true });
  mount(questions.slice(0, 1));
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  const check = screen.getByRole("button", { name: /ตรวจคำตอบ/ });
  await waitFor(() => expect(check).toBeEnabled());
  fireEvent.click(check);
  await screen.findByText("Network error");
  fireEvent.click(check);
  await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
  const [first, second] = mocks.api.mock.calls.slice(1);
  expect(first).toEqual(second);
  expect(first[0]).toBe("/me/practice/chapter-02/q1/attempt");
  expect(first[1]).toMatchObject({ ownerId: "reader-a", method: "POST" });
  expect(JSON.parse(first[1].body)).toMatchObject({
    option_id: "a",
    submission_id: expect.any(String),
  });
  fireEvent.click(screen.getByRole("button", { name: /ดูผลการฝึก/ }));
  await screen.findByText("บันทึกคำตอบในประวัติบัญชีแล้ว");
});

it("keeps a signed-in checkpoint stateless", async () => {
  mocks.ownerId = "reader-a";
  mocks.api.mockResolvedValue(response(true));
  mount(questions.slice(0, 1), "checkpoint");
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
  expect(mocks.api.mock.calls.map(([path]) => path)).toEqual([
    "/learning/practice/chapter-02/q1/check",
  ]);
});

it("reveals preloaded feedback on submit with no guest answer request", () => {
  mount(preloaded);
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  expect(screen.queryByText("木 เป็นรูปต้นไม้")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  expect(screen.getByText("木 เป็นรูปต้นไม้")).toBeInTheDocument();
  expect(mocks.api).not.toHaveBeenCalled();
  expect(localStorage.length).toBe(0);
});

it("grades immediately, queues a failed save across reloads, and reuses its ID", async () => {
  mocks.ownerId = "reader-a";
  mocks.api.mockImplementation((path) => path === "/health"
    ? Promise.resolve({ account_writes_enabled: true })
    : Promise.reject(new Error("Offline")));
  const submit = async () => {
    fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
    const check = screen.getByRole("button", { name: /ตรวจคำตอบ/ });
    await waitFor(() => expect(check).toBeEnabled());
    fireEvent.click(check);
    expect(screen.getByText("ถูกต้อง เชื่อมโยงได้แล้ว!")).toBeInTheDocument();
  };
  const first = mount(preloaded);
  await submit();
  await screen.findByText(/Offline/);
  expect(localStorage.length).toBe(1);
  fireEvent.click(screen.getByRole("button", { name: /ดูผลการฝึก/ }));
  expect(screen.getByText(/คำตอบที่ยังไม่ยืนยันอยู่ในคิว/)).toBeInTheDocument();
  first.unmount();

  const request = mocks.api.mock.calls.at(-1);
  mocks.api.mockImplementation((path) => path === "/health"
    ? Promise.resolve({ account_writes_enabled: true })
    : Promise.resolve({ ...response(true), persisted: true }));
  mount(preloaded);
  await waitFor(() => expect(localStorage.length).toBe(0));
  expect(mocks.api.mock.calls.at(-1)).toEqual(request);
});

it("retries saving from feedback and uses the server grade in the round summary", async () => {
  mocks.ownerId = "reader-a";
  mocks.api
    .mockResolvedValueOnce({ account_writes_enabled: true })
    .mockRejectedValueOnce(new Error("Lost response"))
    .mockResolvedValueOnce({ ...response(false), correct_option_id: "b", correct_text: "ป่า", persisted: true });
  mount(preloaded);
  fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
  const check = screen.getByRole("button", { name: /ตรวจคำตอบ/ });
  await waitFor(() => expect(check).toBeEnabled());
  fireEvent.click(check);
  expect(screen.getByText("ถูกต้อง เชื่อมโยงได้แล้ว!")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: /ลองบันทึกอีกครั้ง/ }));
  await screen.findByText(/อีกนิดเดียว/);
  expect(mocks.api.mock.calls[1]).toEqual(mocks.api.mock.calls[2]);
  fireEvent.click(screen.getByRole("button", { name: /ดูผลการฝึก/ }));
  expect(screen.getByText(/ตอบถูก 0 ข้อ/)).toBeInTheDocument();
  expect(screen.getByText("บันทึกคำตอบในประวัติบัญชีแล้ว")).toBeInTheDocument();
});

it("waits for an account save when browser storage is unavailable", async () => {
  mocks.ownerId = "reader-a";
  const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("Storage unavailable");
  });
  let settle!: (result: ReturnType<typeof response>) => void;
  mocks.api
    .mockResolvedValueOnce({ account_writes_enabled: true })
    .mockReturnValueOnce(new Promise((resolve) => { settle = resolve; }));
  try {
    mount(preloaded);
    fireEvent.click(screen.getByRole("radio", { name: /ต้นไม้/ }));
    const check = screen.getByRole("button", { name: /ตรวจคำตอบ/ });
    await waitFor(() => expect(check).toBeEnabled());
    fireEvent.click(check);
    expect(screen.queryByText("ถูกต้อง เชื่อมโยงได้แล้ว!")).not.toBeInTheDocument();
    settle({ ...response(true), persisted: true });
    await screen.findByText("ถูกต้อง เชื่อมโยงได้แล้ว!");
  } finally {
    setItem.mockRestore();
  }
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
  expect(screen.queryByText("林 มี 木 สองตัว")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "ดูรายละเอียด ข้อ 2" }));
  expect(screen.getByRole("dialog", { name: "ข้อ 2" })).toContainElement(
    screen.getByText("林 มี 木 สองตัว"),
  );
  fireEvent.click(screen.getByRole("button", { name: "ปิดรายละเอียด" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
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
