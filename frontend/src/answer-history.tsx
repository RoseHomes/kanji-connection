import { Eye, X } from "lucide-react";
import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { useStopAudioOnChange } from "./lesson-audio";

function AnswerDetails({
  title,
  status,
  children,
  opener,
  onClose,
}: {
  title: string;
  status: ReactNode;
  children: ReactNode;
  opener: HTMLButtonElement;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useStopAudioOnChange(title);
  useLayoutEffect(() => {
    const element = dialog.current;
    if (!element) return;
    element.showModal();
    return () => {
      if (element.open) element.close();
      if (opener.isConnected) opener.focus({ preventScroll: true });
    };
  }, [opener]);
  return (
    <dialog
      ref={dialog}
      className="answer-details"
      aria-labelledby={titleId}
      onClose={(event) => {
        if (!event.currentTarget.open) onClose();
      }}
    >
      <header>
        <div className="answer-details-heading">
          <h3 id={titleId}>{title}</h3>
          {status}
        </div>
        <button
          type="button"
          className="history-icon-button"
          aria-label="ปิดรายละเอียด"
          autoFocus
          onClick={() => dialog.current?.close()}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </header>
      <div className="answer-details-body content-stack">{children}</div>
    </dialog>
  );
}

export function AnswerHistoryItem({
  title,
  detailTitle = title,
  correct,
  children,
}: {
  title: string;
  detailTitle?: string;
  correct: boolean | null;
  children: ReactNode;
}) {
  const [opener, setOpener] = useState<HTMLButtonElement | null>(null);
  const status = (
    <span className="history-status" data-correct={correct ?? undefined}>
      {correct === null ? "ไม่คิดคะแนน" : correct ? "ถูกต้อง" : "ลองใหม่"}
    </span>
  );
  return (
    <li className="history-item">
      <span className="history-title">{title}</span>
      {status}
      <button
        type="button"
        className="history-icon-button"
        aria-haspopup="dialog"
        aria-label={`ดูรายละเอียด ${detailTitle}`}
        onClick={(event) => setOpener(event.currentTarget)}
      >
        <Eye size={18} aria-hidden="true" />
      </button>
      {opener && (
        <AnswerDetails
          title={detailTitle}
          status={status}
          opener={opener}
          onClose={() => setOpener(null)}
        >
          {children}
        </AnswerDetails>
      )}
    </li>
  );
}
