import { m, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import { ArrowUpRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
export function Reveal({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <m.div
      className={className}
      initial={{ opacity: 1, y: reduce ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.24 }}
    >
      {children}
    </m.div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading content-stack">
      <p className="eyebrow">
        <Sparkles size={15} />
        {eyebrow}
      </p>
      <h1>
        {title}
        <span className="coral">。</span>
      </h1>
      {children && <div className="lead content-stack">{children}</div>}
    </header>
  );
}
export function Chips({
  items,
  value,
  onChange,
  label,
}: {
  items: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <div className="filter-chips" role="group" aria-label={label}>
      {items.map((item) => (
        <button
          type="button"
          key={item.value}
          aria-pressed={value === item.value}
          className={value === item.value ? "chip selected" : "chip"}
          onClick={() => onChange(item.value)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
export function NextStep({
  title,
  body,
  to,
  label,
}: {
  title: string;
  body: string;
  to: string;
  label: string;
}) {
  return (
    <aside className="next-step">
      <div>
        <p className="eyebrow">A LITTLE PRACTICE, A BIG CONNECTION</p>
        <h2>{title}</h2>
        <p>{body}</p>
      </div>
      <Link className="button primary" to={to}>
        {label}
        <ArrowUpRight size={20} />
      </Link>
    </aside>
  );
}
