import { NextResponse } from "next/server";
import { establishIdentity } from "@/server/identity/login";
import { cookieSecure, serializeSessionCookie } from "@/server/identity/sessionCookie";
import { IDENTITY_ROUTE, IDENTITY_SUCCESS_ROUTE } from "@/server/domain/identity";

export const dynamic = "force-dynamic";

function redirectWithError(origin: string, reason: string, email: string): NextResponse {
  const url = new URL(IDENTITY_ROUTE, origin);
  url.searchParams.set("error", reason);
  if (email.trim()) url.searchParams.set("email", email.trim());
  return NextResponse.redirect(url, 303);
}

export async function POST(request: Request) {
  const origin = new URL(request.url).origin;
  const contentType = request.headers.get("content-type") ?? "";
  let email = "";
  let password = "";
  try {
    if (contentType.includes("application/json")) {
      const body = (await request.json()) as { email?: string; password?: string };
      email = String(body.email ?? "");
      password = String(body.password ?? "");
    } else {
      const form = await request.formData();
      email = String(form.get("email") ?? "");
      password = String(form.get("password") ?? "");
    }
  } catch {
    return redirectWithError(origin, "IDENTITY_CREDENTIALS_REJECTED", email);
  }
  const result = await establishIdentity(email, password);
  if (!result.ok) {
    return redirectWithError(origin, result.reason, email);
  }
  const response = NextResponse.redirect(new URL(IDENTITY_SUCCESS_ROUTE, origin), 303);
  response.headers.set("Set-Cookie", serializeSessionCookie(result.token, cookieSecure()));
  return response;
}
