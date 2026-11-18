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
  options: RequestInit & { anonymous?: boolean } = {},
): Promise<T> {
  const { anonymous = false, ...request } = options;
  const { data } =
    supabase && !anonymous
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
      ...request,
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
            ? "ไม่พบเนื้อหาที่เผยแพร่ หรือเนื้อหานี้ยังไม่พร้อมใช้งาน"
            : response.status === 503
              ? "บริการยังไม่พร้อมใช้งาน โปรดลองอีกครั้ง"
              : "ยังโหลดข้อมูลไม่ได้ โปรดลองอีกครั้ง",
      response.status,
    );
  return response.json();
}
