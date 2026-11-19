import { createClient } from "@supabase/supabase-js";

import { publicAuthConfig } from "./auth-config";
export { publicAuthConfig } from "./auth-config";
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
export const supabase =
  import.meta.env.MODE !== "editorial" && publicAuthConfig(url, key)
    ? createClient(url!, key!, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          flowType: "pkce",
        },
      })
    : null;
