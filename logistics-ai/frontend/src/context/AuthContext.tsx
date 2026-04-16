import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import type { AuthSession } from "../types/auth";

function resolveApiBase() {
  const fallback = `${window.location.protocol}//${window.location.hostname}:8000/api`;
  const configured = import.meta.env.VITE_API_BASE;

  if (!configured) {
    return fallback;
  }

  return configured.replace("127.0.0.1", window.location.hostname).replace("localhost", window.location.hostname);
}

const API_BASE = resolveApiBase();

interface AuthContextValue {
  session: AuthSession | null;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  signupWithPassword: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function parseAuthResponse(response: Response, fallbackMessage: string): Promise<AuthSession> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? fallbackMessage);
  }
  return (await response.json()) as AuthSession;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const hydrate = async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          credentials: "include",
        });

        if (!active) {
          return;
        }

        if (response.ok) {
          const user = (await response.json()) as AuthSession["user"];
          setSession({
            authenticated: true,
            expires_at: "",
            refresh_expires_at: "",
            user,
          });
        } else {
          setSession(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void hydrate();
    return () => {
      active = false;
    };
  }, []);

  const loginWithPassword = async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });
    const nextSession = await parseAuthResponse(response, "Email sign-in failed.");
    setSession(nextSession);
  };

  const signupWithPassword = async (name: string, email: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/signup`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name, email, password }),
    });
    const nextSession = await parseAuthResponse(response, "Account creation failed.");
    setSession(nextSession);
  };

  const loginWithGoogle = async (credential: string) => {
    const response = await fetch(`${API_BASE}/auth/google`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ credential }),
    });
    const nextSession = await parseAuthResponse(response, "Google sign-in failed.");
    setSession(nextSession);
  };

  const logout = async () => {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      credentials: "include",
    }).catch(() => undefined);
    setSession(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      loginWithPassword,
      signupWithPassword,
      loginWithGoogle,
      logout,
      isAuthenticated: Boolean(session?.authenticated),
      loading,
    }),
    [loading, session],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
