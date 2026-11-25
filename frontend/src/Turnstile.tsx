import { useEffect, useRef, useState } from "react";

type Widget = {
  render(
    container: HTMLElement,
    options: {
      sitekey: string;
      size: "flexible";
      "response-field": false;
      callback: (token: string) => void;
      "expired-callback": () => void;
      "timeout-callback": () => void;
      "error-callback": () => void;
      "unsupported-callback": () => void;
    },
  ): string;
  remove(id: string): void;
};

const URL =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
const browser = window as Window & { turnstile?: Widget };
let scriptLoad: Promise<Widget> | undefined;

function loadWidget(): Promise<Widget> {
  if (browser.turnstile) return Promise.resolve(browser.turnstile);
  if (!scriptLoad) {
    scriptLoad = new Promise<Widget>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = URL;
      script.async = true;
      const timeout = window.setTimeout(failed, 15_000);

      function failed() {
        window.clearTimeout(timeout);
        script.remove();
        reject(new Error("Turnstile unavailable"));
      }

      script.onerror = failed;
      script.onload = () => {
        window.clearTimeout(timeout);
        if (browser.turnstile) resolve(browser.turnstile);
        else failed();
      };
      document.head.appendChild(script);
    }).catch((error: unknown) => {
      scriptLoad = undefined;
      throw error;
    });
  }
  return scriptLoad;
}

export function Turnstile({
  siteKey,
  onToken,
}: {
  siteKey: string;
  onToken: (token: string | null) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [retry, setRetry] = useState(0);
  const [status, setStatus] = useState<
    "loading" | "pending" | "verified" | "retry"
  >("loading");
  useEffect(() => {
    let active = true;
    let widget: Widget | undefined;
    let id: string | undefined;
    const clear = () => {
      if (!active) return;
      onToken(null);
      setStatus("retry");
    };
    void loadWidget()
      .then((loaded) => {
        if (!active || !container.current) return;
        widget = loaded;
        setStatus("pending");
        id = widget.render(container.current, {
          sitekey: siteKey,
          size: "flexible",
          "response-field": false,
          callback: (token) => {
            if (!active) return;
            onToken(token);
            setStatus("verified");
          },
          "expired-callback": clear,
          "timeout-callback": clear,
          "error-callback": clear,
          "unsupported-callback": clear,
        });
      })
      .catch(clear);
    return () => {
      active = false;
      if (id !== undefined) widget?.remove(id);
    };
  }, [siteKey, onToken, retry]);

  return (
    <div className="content-stack">
      <div ref={container} />
      <p role="status" className="subtle">
        {status === "loading" && "กำลังโหลดการตรวจสอบความปลอดภัย…"}
        {status === "pending" && "โปรดทำการตรวจสอบความปลอดภัยให้เสร็จ"}
        {status === "verified" && "ผ่านการตรวจสอบความปลอดภัยแล้ว"}
        {status === "retry" && "การตรวจสอบหมดอายุหรือยังไม่พร้อมใช้งาน กรุณาลองใหม่"}
      </p>
      {status === "retry" && (
        <div className="action-group">
          <button
            type="button"
            onClick={() => {
              setStatus("loading");
              setRetry((value) => value + 1);
            }}
          >
            เริ่มการตรวจสอบใหม่
          </button>
        </div>
      )}
    </div>
  );
}
