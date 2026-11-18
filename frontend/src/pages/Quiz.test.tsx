import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QuizRound } from "./Quiz";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  localStorage.clear();
});
it("keeps read-only questions inspectable without submitting or saving an answer", () => {
  render(
    <MemoryRouter>
      <QuizRound
        questions={[
          {
            key: "chapter-02:q-01",
            prompt: "木",
            question_type: "reading",
            options: [],
            manual: false,
          },
        ]}
        persist={true}
        readOnly={true}
        onSaved={() => {}}
      />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "き" } });
  expect(screen.getByRole("button", { name: "ตรวจคำตอบ" })).toBeDisabled();
  fireEvent.submit(screen.getByRole("textbox").closest("form")!);
  expect(mocks.api).not.toHaveBeenCalled();
});
it("submits answers once, shows feedback, and keeps comparison responses ungraded", async () => {
  mocks.api.mockResolvedValueOnce({
    correct: true,
    status: "graded",
    expected: "き",
    explanation: "",
  });
  render(
    <MemoryRouter>
      <QuizRound
        questions={[
          {
            key: "chapter-02:q-01",
            prompt: "木",
            question_type: "reading",
            options: [],
            manual: false,
          },
          {
            key: "chapter-02:comparison-c",
            prompt: "Compare",
            question_type: "comparison",
            options: [],
            manual: true,
          },
        ]}
        persist={false}
        onSaved={() => {}}
      />
    </MemoryRouter>,
  );
  expect(screen.queryByText("คำตอบอ้างอิง:")).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "き" } });
  fireEvent.click(screen.getByRole("button", { name: "ตรวจคำตอบ" }));
  await screen.findByText("ถูกต้อง ✓");
  const request = JSON.parse(mocks.api.mock.calls[0][1].body);
  expect(request.answer).toBe("き");
  expect(request.submission_id).toBeTruthy();
  expect(request.score).toBeUndefined();
  fireEvent.click(screen.getByRole("button", { name: "ข้อถัดไป →" }));
  mocks.api.mockResolvedValueOnce({
    correct: null,
    status: "needs_manual_review",
    expected: null,
    explanation: "source note",
  });
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "source explanation" },
  });
  fireEvent.click(screen.getByRole("button", { name: "ส่งคำอธิบาย" }));
  await screen.findByText("รอผู้สอนตรวจ · ยังไม่คิดคะแนน");
  fireEvent.click(screen.getByRole("button", { name: "ข้อถัดไป →" }));
  await screen.findByText(/ตอบถูก 1 จาก 1 ข้อที่ตรวจอัตโนมัติ/);
});
it("reuses the same submission identifier on a failed save retry", async () => {
  mocks.api.mockRejectedValueOnce(new Error("Retry")).mockResolvedValueOnce({
    correct: false,
    status: "graded",
    expected: "き",
    explanation: "",
  });
  render(
    <MemoryRouter>
      <QuizRound
        questions={[
          {
            key: "chapter-02:q-01",
            prompt: "木",
            question_type: "reading",
            options: [],
            manual: false,
          },
        ]}
        persist={true}
        onSaved={() => {}}
      />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "wrong" } });
  fireEvent.click(screen.getByRole("button", { name: "ตรวจคำตอบ" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "ตรวจคำตอบ" }));
  await waitFor(() => expect(mocks.api).toHaveBeenCalledTimes(2));
  expect(mocks.api.mock.calls[0][1].body).toBe(mocks.api.mock.calls[1][1].body);
  expect(mocks.api.mock.calls[1][0]).toContain("/me/attempts/");
});
