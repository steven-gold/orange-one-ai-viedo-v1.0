export const SESSION_COOKIE_NAME = "acpos_session";
export const SESSION_MAX_AGE_SECONDS = 43200;

export function parseSessionCookie(cookieHeader: string | null): string {
  if (!cookieHeader) return "";
  const parts = cookieHeader.split(";");
  for (const part of parts) {
    const [name, ...rest] = part.trim().split("=");
    if (name === SESSION_COOKIE_NAME) return decodeURIComponent(rest.join("="));
  }
  return "";
}

export function serializeSessionCookie(token: string, secure: boolean): string {
  const flags = [
    `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${SESSION_MAX_AGE_SECONDS}`,
  ];
  if (secure) flags.push("Secure");
  return flags.join("; ");
}

export function clearSessionCookie(secure: boolean): string {
  const flags = [
    `${SESSION_COOKIE_NAME}=`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    "Max-Age=0",
  ];
  if (secure) flags.push("Secure");
  return flags.join("; ");
}

export function cookieSecure(): boolean {
  if (process.env.NODE_ENV === "production") return true;
  const env = (process.env.ACPOS_DEPLOYMENT_ENV ?? "").toLowerCase();
  return env === "production";
}
