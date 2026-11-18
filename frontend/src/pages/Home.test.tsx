import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Home from "./Home";
afterEach(cleanup);
it("changes the teaching illustration and reading when a kanji is selected", () => {
  render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("img", { name: "ภาพช่วยจำต้นไม้ 1 ต้น" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "森" }));
  expect(screen.getByRole("button", { name: "森" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    screen.getByRole("img", { name: "ภาพช่วยจำต้นไม้ 3 ต้น" }),
  ).toBeInTheDocument();
  expect(screen.getByText("もり · mori")).toBeInTheDocument();
});
