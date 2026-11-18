export function publicAuthConfig(
  url: string | undefined,
  key: string | undefined,
) {
  if (
    !url ||
    !key ||
    url.includes("your-project") ||
    key.includes("your-publishable")
  )
    return false;
  try {
    const parsed = new URL(url);
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      parsed.search ||
      parsed.hash ||
      !["", "/"].includes(parsed.pathname)
    )
      return false;
    if (key.startsWith("sb_publishable_")) return true;
    if (key.startsWith("sb_secret_")) return false;
    const payload = JSON.parse(
      atob(key.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
    );
    return payload.role === "anon";
  } catch {
    return false;
  }
}

export function requirePublicAuthConfig(
  url: string | undefined,
  key: string | undefined,
) {
  if (key && !key.includes("your-publishable") && !publicAuthConfig(url, key)) {
    throw new Error(
      "Frontend Auth requires a valid HTTPS project origin and public publishable/anon key. Server secrets must never enter browser bundles.",
    );
  }
}
