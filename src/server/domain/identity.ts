export const IDENTITY_SURFACE_UID = "identity:login";
export const IDENTITY_ROUTE = "/login";
export const IDENTITY_LOGIN_PATH = "/identity/login";
export const IDENTITY_SESSION_PATH = "/v1/identity/session";
export const IDENTITY_SUCCESS_ROUTE = "/";

export const LOGIN_REASON_CODES = [
  "IDENTITY_CREDENTIALS_REJECTED",
  "DATABASE_RUNTIME_NOT_BOUND",
  "APP_USERS_EMAIL_JOIN_NOT_FOUND",
  "IDENTITY_SESSION_CREATE_FAILED",
] as const;

export type LoginReasonCode = (typeof LOGIN_REASON_CODES)[number];

export function isLoginReasonCode(value: string): value is LoginReasonCode {
  return (LOGIN_REASON_CODES as readonly string[]).includes(value);
}
