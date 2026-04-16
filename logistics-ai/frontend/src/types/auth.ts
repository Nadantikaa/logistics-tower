export interface AuthUser {
  id: number;
  role: "user" | "admin";
  display_name: string;
}

export interface AuthSession {
  authenticated: boolean;
  expires_at: string;
  refresh_expires_at: string;
  user: AuthUser;
}

export interface MfaChallenge {
  authenticated: false;
  mfa_required: true;
  challenge_id: string;
  expires_at: string;
  channel: "email";
}

export type AuthResult = AuthSession | MfaChallenge;
