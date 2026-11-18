import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "./supabase";

const Context = createContext<{
  session: Session | null;
  ready: boolean;
  configured: boolean;
}>({ session: null, ready: false, configured: false });
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(!supabase);
  const client = useQueryClient();
  useEffect(() => {
    if (!supabase) return;
    let active = true;
    let observed = false;
    let subject: string | null = null;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, value) => {
      if (active) {
        observed = true;
        if (subject !== (value?.user.id || null)) client.clear();
        subject = value?.user.id || null;
        setSession(value);
        setReady(true);
      }
    });
    void supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (active && !observed) {
          subject = data.session?.user.id || null;
          setSession(error ? null : data.session);
          setReady(true);
        }
      })
      .catch(() => {
        if (active && !observed) {
          setSession(null);
          setReady(true);
        }
      });
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [client]);
  return (
    <Context.Provider value={{ session, ready, configured: !!supabase }}>
      {children}
    </Context.Provider>
  );
}
export const useAuth = () => useContext(Context);
