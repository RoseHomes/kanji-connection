const MIN_PASSWORD_LENGTH = 12;

export function passwordIssue(password: string, email: string) {
  if ([...password].length < MIN_PASSWORD_LENGTH)
    return "ใช้รหัสผ่านอย่างน้อย 12 อักขระ";
  if (new TextEncoder().encode(password).length > 72)
    return "รหัสผ่านยาวเกินไป ลองลดจำนวนอักขระ";

  const normalize = (value: string) =>
    value.normalize("NFKC").trim().toLowerCase();
  const candidate = normalize(password);
  const address = normalize(email);
  const separator = address.lastIndexOf("@");
  const localPart = separator > 0 ? address.slice(0, separator) : "";
  if (
    address &&
    (candidate === address || (localPart && candidate === localPart))
  )
    return "รหัสผ่านต้องไม่ตรงกับอีเมลหรือชื่อก่อนเครื่องหมาย @";

  const compact = candidate.replace(/[\s._-]/g, "");
  const obviousBase =
    /^(?:password|passw0rd|qwerty|letmein|welcome|changeme|admin|iloveyou|1234567890)[0-9\p{P}\p{S}]*$/u;
  if (
    !compact ||
    obviousBase.test(compact) ||
    /^(.{1,4})\1+$/u.test(compact) ||
    /^\d{12,}$/u.test(compact) ||
    "abcdefghijklmnopqrstuvwxyz".includes(compact) ||
    "zyxwvutsrqponmlkjihgfedcba".includes(compact) ||
    "qwertyuiopasdfghjklzxcvbnm".includes(compact)
  ) {
    return "รหัสผ่านเดาง่ายเกินไป ลองใช้วลีที่เดายากหรือรหัสจากโปรแกรมจัดการรหัสผ่าน";
  }
  return null;
}
