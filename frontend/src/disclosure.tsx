import { useId, useState, type ReactNode } from "react";
import { m, AnimatePresence, useReducedMotion } from "motion/react";
import { ChevronDown } from "lucide-react";

export function Disclosure({
  label,
  children,
  initialOpen = false,
}: {
  label: ReactNode;
  children: ReactNode;
  initialOpen?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen),
    id = useId(),
    reduce = useReducedMotion();
  return (
    <div className="learning-disclosure">
      <button
        type="button"
        className="disclosure-trigger"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        {label}
        <ChevronDown size={18} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <m.div
            id={id}
            className="disclosure-panel"
            initial={{ height: reduce ? "auto" : 0, opacity: reduce ? 1 : 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: reduce ? "auto" : 0, opacity: 0 }}
            transition={{ duration: reduce ? 0 : 0.2 }}
          >
            <div>{children}</div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
