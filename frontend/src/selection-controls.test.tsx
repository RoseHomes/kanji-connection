import { afterEach, expect, it } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import { ChoicePicker, SegmentedControl } from "./selection-controls";
afterEach(cleanup);
function Picker() {
  const [value, setValue] = useState("one");
  return (
    <ChoicePicker
      label="เลือกบท"
      value={value}
      onChange={setValue}
      options={[
        { value: "one", label: "บทหนึ่ง" },
        { value: "two", label: "บทสอง" },
        { value: "three", label: "บทสาม" },
      ]}
    />
  );
}
it("opens with keyboard, exposes a listbox and restores focus on Escape", async () => {
  render(<Picker />);
  const trigger = screen.getByRole("combobox", { name: "เลือกบท" });
  trigger.focus();
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
  await screen.findByRole("listbox");
  expect(screen.getAllByRole("option")).toHaveLength(3);
  fireEvent.keyDown(screen.getByRole("option", { name: "บทหนึ่ง" }), {
    key: "Escape",
  });
  await waitFor(() =>
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument(),
  );
  await waitFor(() => expect(trigger).toHaveFocus());
});
it("selects a labelled option without typing", async () => {
  render(<Picker />);
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "Enter" });
  const option = await screen.findByRole("option", { name: "บทสอง" });
  fireEvent.keyDown(option, { key: "Enter" });
  await waitFor(() =>
    expect(screen.getByRole("combobox")).toHaveTextContent("บทสอง"),
  );
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
it("disables an empty picker without fabricating options", () => {
  render(
    <ChoicePicker label="ว่าง" options={[]} value="" onChange={() => {}} />,
  );
  expect(screen.getByRole("combobox")).toBeDisabled();
});
it("announces selected mode with a visible marker and accessible pressed state", () => {
  function Modes() {
    const [value, setValue] = useState("guided");
    return (
      <SegmentedControl
        label="รูปแบบ"
        value={value}
        options={[
          { value: "guided", label: "เป็นช่วง" },
          { value: "full", label: "ทั้งหมด" },
        ]}
        onChange={setValue}
      />
    );
  }
  render(<Modes />);
  fireEvent.click(screen.getByRole("button", { name: "ทั้งหมด" }));
  expect(screen.getByRole("button", { name: "ทั้งหมด" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.getByRole("button", { name: "เป็นช่วง" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});
