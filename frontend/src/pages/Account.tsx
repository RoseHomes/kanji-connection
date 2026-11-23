import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../supabase";
import { useAuth } from "../auth";
import { Turnstile } from "../Turnstile";
import { passwordIssue } from "../password-policy";

type Mode = "login" | "signup" | "reset";
type AuthFailure = { status?: number; code?: string };
const tryLater = "ส่งคำขอบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่";
const weakPassword = "รหัสผ่านไม่ผ่านเกณฑ์ความปลอดภัย กรุณาเลือกรหัสผ่านใหม่ที่เดายาก";
const emailNotice = {
  signup:
    "หากอีเมลนี้ใช้สมัครได้ ระบบจะส่งลิงก์ยืนยัน กรุณาตรวจกล่องจดหมายและรอสักครู่ก่อนส่งคำขออีกครั้ง",
  reset:
    "หากมีบัญชีที่ใช้อีเมลนี้ ระบบจะส่งลิงก์ตั้งรหัสผ่านใหม่ กรุณาตรวจกล่องจดหมายและรอสักครู่ก่อนส่งคำขออีกครั้ง",
};
const privateEmailErrors = new Set([
  "over_email_send_rate_limit",
  "user_already_exists",
  "email_exists",
  "user_not_found",
  "email_not_confirmed",
]);

function rateLimited(error: AuthFailure) {
  return error.status === 429 || !!error.code?.startsWith("over_");
}

function authMessage(error: AuthFailure, mode: Mode) {
  // A per-address email throttle can itself disclose whether an account exists.
  if (mode !== "login" && privateEmailErrors.has(error.code ?? ""))
    return emailNotice[mode];
  if (rateLimited(error)) return tryLater;
  if (error.code === "captcha_failed")
    return "ยืนยันการตรวจสอบความปลอดภัยไม่สำเร็จ กรุณาทำการตรวจสอบใหม่";
  if (mode === "signup" && error.code === "weak_password") return weakPassword;
  return mode === "login"
    ? "เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจอีเมลและรหัสผ่าน แล้วลองใหม่"
    : "ดำเนินการไม่สำเร็จ กรุณาลองใหม่ในภายหลัง";
}

export default function Account() {
  const {
    session,
    ready,
    configured,
    recoveringPassword,
    finishPasswordRecovery,
  } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [challenge, setChallenge] = useState(0);
  const siteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY?.trim();
  const navigate = useNavigate();
  const signup = mode === "signup";
  const reset = mode === "reset";

  function switchMode(next: Mode) {
    setMode(next);
    setPassword("");
    setMessage("");
    setCaptchaToken(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!supabase || submitting.current || (siteKey && !captchaToken)) return;
    const address = email.trim();
    const issue = signup ? passwordIssue(password, address) : null;
    if (issue) {
      setMessage(issue);
      return;
    }
    const captcha = captchaToken ? { captchaToken } : {};
    submitting.current = true;
    setBusy(true);
    setMessage("");
    try {
      const redirectTo = `${window.location.origin}/account`;
      if (reset) {
        const { error } = await supabase.auth.resetPasswordForEmail(address, {
          redirectTo,
          ...captcha,
        });
        setMessage(error ? authMessage(error, mode) : emailNotice.reset);
        return;
      }
      const { data, error } = signup
        ? await supabase.auth.signUp({
            email: address,
            password,
            options: { emailRedirectTo: redirectTo, ...captcha },
          })
        : await supabase.auth.signInWithPassword({
            email: address,
            password,
            options: captcha,
          });
      if (data.session) navigate("/dashboard");
      else if (error) setMessage(authMessage(error, mode));
      else if (signup) setMessage(emailNotice.signup);
    } catch {
      setMessage("เชื่อมต่อไม่ได้ กรุณาลองอีกครั้ง");
    } finally {
      submitting.current = false;
      setBusy(false);
      setPassword("");
      setCaptchaToken(null);
      setChallenge((value) => value + 1);
    }
  }

  return (
    <div className="page section account-page">
      <aside className="account-intro">
        <p className="eyebrow">A SPACE OF YOUR OWN</p>
        <span className="account-glyph" lang="ja" aria-hidden="true">
          学
        </span>
        <h2>
          เริ่มเรียนก่อนได้
          <br />
          มีบัญชีเมื่อคุณพร้อม
        </h2>
        <p>บทเรียนสาธารณะเปิดให้ทุกคน ส่วนความก้าวหน้าและประวัติการเรียนเป็นพื้นที่ของคุณ</p>
        <Link className="text-link" to="/lessons">
          กลับไปเรียนโดยไม่เข้าสู่ระบบ →
        </Link>
      </aside>
      <section className="account-panel">
        <p className="eyebrow">YOUR LEARNING SPACE</p>
        <h1>
          {recoveringPassword
            ? "ตั้งรหัสผ่านใหม่"
            : session
              ? "บัญชีของคุณ"
              : reset
                ? "ตั้งรหัสผ่านใหม่"
                : signup
                  ? "เริ่มเส้นทางการเรียนรู้"
                  : "ยินดีต้อนรับกลับ"}
        </h1>
        {!ready ? (
          <p role="status">กำลังตรวจบัญชี…</p>
        ) : session ? (
          <SignedInAccount
            key={session.user.id}
            email={session.user.email ?? ""}
            recovering={recoveringPassword}
            onRecoveryFinished={finishPasswordRecovery}
            onSignedOut={() => switchMode("login")}
          />
        ) : (
          <>
            {!configured && (
              <p className="notice">
                ยังไม่ได้ตั้งค่าบัญชี คุณยังเรียนและทำแบบฝึกหัดสาธารณะได้
              </p>
            )}
            <form
              onSubmit={(event) => void submit(event)}
              className="learning-form"
            >
              <label>
                อีเมล
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              {!reset && (
                <label>
                  รหัสผ่าน
                  <input
                    type="password"
                    autoComplete={signup ? "new-password" : "current-password"}
                    maxLength={128}
                    required
                    value={password}
                    aria-describedby={
                      signup ? "signup-password-hint" : undefined
                    }
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>
              )}
              {signup && (
                <p id="signup-password-hint" className="subtle">
                  ใช้อย่างน้อย 12 อักขระ และหลีกเลี่ยงอีเมลหรือรหัสผ่านที่เดาง่าย
                </p>
              )}
              {reset && (
                <p className="subtle">เปิดลิงก์ในเบราว์เซอร์เดียวกับที่ส่งคำขอ</p>
              )}
              {configured && siteKey && (
                <Turnstile
                  key={`${mode}-${challenge}`}
                  siteKey={siteKey}
                  onToken={setCaptchaToken}
                />
              )}
              <button
                className="primary"
                disabled={!configured || busy || (!!siteKey && !captchaToken)}
              >
                {busy
                  ? "กำลังดำเนินการ…"
                  : reset
                    ? "ส่งลิงก์ตั้งรหัสผ่านใหม่"
                    : signup
                      ? "สมัครสมาชิก"
                      : "เข้าสู่ระบบ"}
              </button>
            </form>
            <div className="account-form-actions">
              <button
                className="text-link"
                disabled={busy}
                onClick={() => switchMode(mode === "login" ? "signup" : "login")}
              >
                {reset
                  ? "กลับไปเข้าสู่ระบบ"
                  : signup
                    ? "มีบัญชีแล้ว · เข้าสู่ระบบ"
                    : "ยังไม่มีบัญชี · สมัครสมาชิก"}
              </button>
              {mode === "login" && (
                <button
                  className="text-link"
                  disabled={busy}
                  onClick={() => switchMode("reset")}
                >
                  ลืมรหัสผ่าน?
                </button>
              )}
            </div>
            {message && (
              <p role="status" className="notice">
                {message}
              </p>
            )}
          </>
        )}
        <p className="subtle">
          ข้อมูลเดิมในเบราว์เซอร์จะไม่ถูกส่งไปยังบัญชีอัตโนมัติ
          คุณเลือกตรวจและซิงก์ได้ที่แดชบอร์ดเมื่อเปิดให้บันทึก
        </p>
      </section>
    </div>
  );
}

function SignedInAccount({
  email,
  recovering,
  onRecoveryFinished,
  onSignedOut,
}: {
  email: string;
  recovering: boolean;
  onRecoveryFinished: () => void;
  onSignedOut: () => void;
}) {
  const [changing, setChanging] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);

  async function updatePassword(event: FormEvent) {
    event.preventDefault();
    if (!supabase || submitting.current) return;
    const issue = passwordIssue(password, email);
    if (issue) {
      setMessage(issue);
      return;
    }
    submitting.current = true;
    setBusy(true);
    setMessage("");
    try {
      const { error } = await supabase.auth.updateUser({
        password,
        ...(recovering ? {} : { current_password: currentPassword }),
      });
      if (!error) {
        onRecoveryFinished();
        setChanging(false);
        setMessage("บันทึกรหัสผ่านใหม่แล้ว");
      } else if (rateLimited(error)) {
        setMessage(tryLater);
      } else if (error.code === "weak_password") {
        setMessage(weakPassword);
      } else if (error.code === "same_password") {
        setMessage("กรุณาใช้รหัสผ่านที่ต่างจากรหัสผ่านปัจจุบัน");
      } else if (error.code === "reauthentication_needed") {
        setMessage("กรุณาออกจากระบบแล้วเข้าสู่ระบบใหม่ก่อนเปลี่ยนรหัสผ่าน");
      } else {
        setMessage("เปลี่ยนรหัสผ่านไม่สำเร็จ กรุณาตรวจข้อมูลแล้วลองใหม่");
      }
    } catch {
      setMessage("เชื่อมต่อไม่ได้ กรุณาลองอีกครั้ง");
    } finally {
      submitting.current = false;
      setBusy(false);
      setPassword("");
      setCurrentPassword("");
    }
  }

  async function signout() {
    if (!supabase || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    try {
      const { error } = await supabase.auth.signOut({ scope: "local" });
      if (error)
        setMessage(
          rateLimited(error) ? tryLater : "ออกจากระบบไม่สำเร็จ กรุณาลองอีกครั้ง",
        );
      else onSignedOut();
    } catch {
      setMessage("เชื่อมต่อไม่ได้ กรุณาลองอีกครั้ง");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <>
      <div className="notice">
        <p>{email}</p>
        <div className="hero-actions">
          {!recovering && (
            <Link className="button primary" to="/dashboard">
              ดูความก้าวหน้า
            </Link>
          )}
          {!recovering && !changing && (
            <button
              disabled={busy}
              onClick={() => {
                setMessage("");
                setChanging(true);
              }}
            >
              เปลี่ยนรหัสผ่าน
            </button>
          )}
          <button disabled={busy} onClick={() => void signout()}>
            ออกจากระบบ
          </button>
        </div>
      </div>
      {(recovering || changing) && (
        <form
          className="learning-form"
          onSubmit={(event) => void updatePassword(event)}
        >
          {!recovering && (
            <label>
              รหัสผ่านปัจจุบัน
              <input
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
            </label>
          )}
          <label>
            รหัสผ่านใหม่
            <input
              type="password"
              autoComplete="new-password"
              required
              aria-describedby="update-password-hint"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <p id="update-password-hint" className="subtle">
            ใช้อย่างน้อย 12 อักขระ และหลีกเลี่ยงอีเมลหรือรหัสผ่านที่เดาง่าย
          </p>
          <button className="primary" disabled={busy}>
            {busy ? "กำลังบันทึก…" : "บันทึกรหัสผ่านใหม่"}
          </button>
        </form>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
    </>
  );
}
