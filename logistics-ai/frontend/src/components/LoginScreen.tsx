import { type FormEvent, useEffect, useRef, useState } from "react";

import { useAuth } from "../context/AuthContext";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (element: HTMLElement, options: Record<string, string>) => void;
        };
      };
    };
  }
}

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.getElementById(GOOGLE_SCRIPT_ID);
    if (existing) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Unable to load Google Sign-In."));
    document.head.appendChild(script);
  });
}

export function LoginScreen() {
  const { loginWithGoogle, loginWithPassword, signupWithPassword } = useAuth();
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleStatus, setGoogleStatus] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    let active = true;

    if (mode !== "login") {
      return () => {
        active = false;
      };
    }

    setGoogleStatus("loading");

    if (!GOOGLE_CLIENT_ID || GOOGLE_CLIENT_ID.includes("your-google-client-id")) {
      setGoogleStatus("unavailable");
      return () => {
        active = false;
      };
    }

    void loadGoogleScript()
      .then(() => {
        if (!active || !window.google || !googleButtonRef.current) {
          return;
        }

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: ({ credential }) => {
            void (async () => {
              try {
                setSubmitting(true);
                setError(null);
                await loginWithGoogle(credential);
              } catch (authError) {
                setError(authError instanceof Error ? authError.message : "Google sign-in failed.");
              } finally {
                setSubmitting(false);
              }
            })();
          },
        });

        googleButtonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(googleButtonRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: "356",
        });
        setGoogleStatus("ready");
      })
      .catch((scriptError) => {
        if (active) {
          setGoogleStatus("unavailable");
          setError(scriptError instanceof Error ? scriptError.message : "Unable to load Google Sign-In.");
        }
      });

    return () => {
      active = false;
    };
  }, [loginWithGoogle, mode]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (mode === "signup") {
        await signupWithPassword(name, email, password);
      } else {
        await loginWithPassword(email, password);
      }
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-card">
        <h1>{mode === "signup" ? "Create account" : "Sign in"}</h1>
        <p className="login-copy">Log in to continue to the control tower.</p>
        <div className="auth-toggle">
          <button
            type="button"
            className={mode === "login" ? "auth-toggle-button active" : "auth-toggle-button"}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            className={mode === "signup" ? "auth-toggle-button active" : "auth-toggle-button"}
            onClick={() => setMode("signup")}
          >
            Create account
          </button>
        </div>

        {mode === "login" ? (
          <div className="social-login-block">
            <div
              ref={googleButtonRef}
              className="google-signin-slot"
            />
            {googleStatus === "loading" ? <p className="google-help-text">Loading Google Sign-In...</p> : null}
            {googleStatus === "unavailable" ? (
              <p className="google-help-text">
                Google Sign-In is unavailable. Check `frontend/.env`, your client ID, and restart Vite.
              </p>
            ) : null}
            <div className="login-divider">or continue with email</div>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "signup" ? (
            <label>
              Full name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Vaishnavi Peru"
                autoComplete="name"
              />
            </label>
          ) : null}
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
            />
          </label>
          <button type="submit" className="auth-submit-button" disabled={submitting}>
            {submitting ? "Please wait..." : mode === "signup" ? "Create account" : "Sign in"}
          </button>
        </form>
        {error ? <p className="login-error">{error}</p> : null}
      </section>
    </main>
  );
}
