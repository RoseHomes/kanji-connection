import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../supabase";
import { useAuth } from "../auth";
export default function Account() {
  const { session, ready, configured } = useAuth();
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setMessage("");
    try {
      const { data, error } = signup
        ? await supabase.auth.signUp({
            email,
            password,
            options: { emailRedirectTo: `${window.location.origin}/account` },
          })
        : await supabase.auth.signInWithPassword({ email, password });
      if (error) setMessage("ดำเนินการไม่ได้ กรุณาตรวจอีเมล รหัสผ่าน และการยืนยันอีเมล");
      else if (data.session) navigate("/dashboard");
      else setMessage("กรุณาตรวจอีเมลเพื่อยืนยันบัญชี แล้วกลับมาเข้าสู่ระบบ");
    } catch {
      setMessage("เชื่อมต่อไม่ได้ กรุณาลองอีกครั้ง");
    } finally {
      setBusy(false);
      setPassword("");
    }
  }
  async function signout() {
    if (!supabase) return;
    setBusy(true);
    try {
      const { error } = await supabase.auth.signOut({ scope: "local" });
      if (error) setMessage("ออกจากระบบไม่สำเร็จ กรุณาลองอีกครั้ง");
    } catch {
      setMessage("เชื่อมต่อไม่ได้ กรุณาลองอีกครั้ง");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page section account-page">
      <p className="eyebrow">YOUR LEARNING SPACE</p>
      <h1>
        {session ? "บัญชีของคุณ" : signup ? "เริ่มเส้นทางการเรียนรู้" : "ยินดีต้อนรับกลับ"}
      </h1>
      {!ready ? (
        <p role="status">กำลังตรวจบัญชี…</p>
      ) : session ? (
        <div className="notice">
          <p>{session.user.email}</p>
          <Link className="button primary" to="/dashboard">
            ดูความก้าวหน้า
          </Link>{" "}
          <button disabled={busy} onClick={() => void signout()}>
            ออกจากระบบ
          </button>
        </div>
      ) : (
        <>
          {!configured && (
            <p className="notice">ยังไม่ได้ตั้งค่าบัญชี คุณยังเรียนและบันทึกแบบผู้เยี่ยมชมได้</p>
          )}
          <form onSubmit={(e) => void submit(e)} className="learning-form">
            <label>
              อีเมล
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              รหัสผ่าน
              <input
                type="password"
                autoComplete={signup ? "new-password" : "current-password"}
                minLength={8}
                maxLength={128}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button className="primary" disabled={!configured || busy}>
              {busy ? "กำลังดำเนินการ…" : signup ? "สมัครสมาชิก" : "เข้าสู่ระบบ"}
            </button>
          </form>
          <button
            className="text-link"
            onClick={() => {
              setSignup(!signup);
              setMessage("");
            }}
          >
            {signup ? "มีบัญชีแล้ว · เข้าสู่ระบบ" : "ยังไม่มีบัญชี · สมัครสมาชิก"}
          </button>
        </>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <p className="subtle">
        ข้อมูลผู้เยี่ยมชมจะไม่ถูกส่งไปยังบัญชีอัตโนมัติ คุณเลือกตรวจและซิงก์ได้ที่แดชบอร์ด
      </p>
    </div>
  );
}
