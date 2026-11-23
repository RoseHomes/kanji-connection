import { publicAuthConfig } from "./auth-config.ts";

// Vite treats these as prefixes. Validation below rejects suffix variants too.
export const PUBLIC_BROWSER_ENV_PREFIXES = [
  "VITE_API_URL",
  "VITE_SUPABASE_URL",
  "VITE_SUPABASE_PUBLISHABLE_KEY",
  "VITE_TURNSTILE_SITE_KEY",
];

function exactHttpsOrigin(value: string | undefined) {
  if (!value || /YOUR_|REPLACE_|PROJECT_REF/i.test(value)) return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      url.origin === value &&
      !url.username &&
      !url.password &&
      !["localhost", "127.0.0.1", "[::1]", "0.0.0.0"].includes(url.hostname) &&
      !url.hostname.startsWith("127.") &&
      !url.hostname.endsWith(".localhost")
    );
  } catch {
    return false;
  }
}

export function requireProductionConfig(
  env: Record<string, string | undefined>,
) {
  if (
    Object.entries(env).some(
      ([name, value]) =>
        value &&
        name.startsWith("VITE_") &&
        !PUBLIC_BROWSER_ENV_PREFIXES.includes(name),
    )
  ) {
    throw new Error(
      "Production browser configuration allows only the API origin, public Supabase configuration, and a Turnstile site key; remove other VITE_ variables.",
    );
  }
  if (!exactHttpsOrigin(env.VITE_API_URL)) {
    throw new Error(
      "Production requires VITE_API_URL as an exact backend HTTPS origin, without a path or trailing slash.",
    );
  }
  if (
    !exactHttpsOrigin(env.VITE_SUPABASE_URL) ||
    !publicAuthConfig(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_PUBLISHABLE_KEY)
  ) {
    throw new Error(
      "Production requires an exact Supabase HTTPS origin and a public publishable/anon key.",
    );
  }
}
