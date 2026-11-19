import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import { useId } from "react";

export interface SelectionOption {
  value: string;
  label: string;
  description?: string;
}

/** Select-only, never a required text field. Radix manages focus, typeahead,
 * Home/End, arrows, Escape, touch dismissal and portalled collision handling. */
export function ChoicePicker({
  label,
  value,
  options,
  onChange,
  placeholder = "เลือกจากรายการ",
  disabled = false,
  triggerLabel,
}: {
  label: string;
  value: string;
  options: SelectionOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  triggerLabel?: string;
}) {
  const id = useId();
  return (
    <div className="choice-picker">
      <label id={id}>{label}</label>
      <Select.Root
        value={options.some((option) => option.value === value) ? value : ""}
        onValueChange={onChange}
        disabled={disabled || !options.length}
      >
        <Select.Trigger className="picker-trigger" aria-labelledby={id}>
          <Select.Value placeholder={placeholder}>{triggerLabel}</Select.Value>
          <Select.Icon>
            <ChevronDown size={18} />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content
            className="picker-content"
            position="popper"
            sideOffset={8}
            collisionPadding={12}
            align="start"
          >
            <Select.ScrollUpButton className="picker-scroll">
              <ChevronUp size={17} />
            </Select.ScrollUpButton>
            <Select.Viewport className="picker-viewport">
              {options.map((o) => (
                <Select.Item
                  className="picker-option"
                  key={o.value}
                  value={o.value}
                  textValue={o.label}
                >
                  <div>
                    <Select.ItemText>{o.label}</Select.ItemText>
                    {o.description && <small>{o.description}</small>}
                  </div>
                  <Select.ItemIndicator>
                    <Check size={18} />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
            <Select.ScrollDownButton className="picker-scroll">
              <ChevronDown size={17} />
            </Select.ScrollDownButton>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </div>
  );
}

export function SegmentedControl({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: SelectionOption[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="segmented-control" role="group" aria-label={label}>
      {options.map((o) => (
        <button
          type="button"
          aria-pressed={value === o.value}
          key={o.value}
          onClick={() => onChange(o.value)}
        >
          {value === o.value && <Check size={16} />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}
