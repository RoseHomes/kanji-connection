import { supabase } from "./supabase";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { data } = supabase
    ? await supabase.auth.getSession()
    : { data: { session: null } };
  const headers = new Headers(options.headers);
  if (data.session)
    headers.set("Authorization", `Bearer ${data.session.access_token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  const timeout = AbortSignal.timeout(15000);
  const response = await fetch(
    `${import.meta.env.VITE_API_URL || ""}/api/v1${path}`,
    {
      ...options,
      headers,
      signal: options.signal
        ? AbortSignal.any([options.signal, timeout])
        : timeout,
    },
  ).catch(() => {
    throw new ApiError("การเชื่อมต่อขัดข้องหรือใช้เวลานานเกินไป โปรดลองใหม่", 0);
  });
  if (!response.ok)
    throw new ApiError(
      response.status === 409
        ? "ข้อมูลเปลี่ยนแล้ว กรุณาโหลดใหม่และเลือกอีกครั้ง"
        : response.status === 401
          ? "กรุณาเข้าสู่ระบบอีกครั้ง"
          : response.status === 404
            ? "ไม่พบเนื้อหาที่บัญชีนี้เข้าถึงได้ กรุณาเลือกบทเรียนอื่นหรือเข้าสู่ระบบ"
            : response.status === 503
              ? "บริการยังไม่พร้อม กรุณาตรวจการตั้งค่าหรือลองใหม่"
              : "ยังโหลดข้อมูลไม่ได้ โปรดลองอีกครั้ง",
      response.status,
    );
  return response.json();
}
