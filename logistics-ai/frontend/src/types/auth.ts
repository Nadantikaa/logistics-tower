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
