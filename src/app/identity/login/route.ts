import { NextRequest, NextResponse } from "next/server";
import {
  IDENTITY_COOKIE_NAME,
  SESSION_TTL_SECONDS,
  createIdentitySession,
} from "@/server/identity/identityRuntime";

function cookieSecure(request: NextRequest): boolean {
  return (
    request.nextUrl.protocol === "https:" ||
    request.headers.get("x-forwarded-proto") === "https" ||
    process.env.ACPOS_DEPLOYMENT_ENV === "production"
  );
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "");
  const password = String(form.get("password") ?? "");
  const created = await createIdentitySession(email, password);
  if (!created.ok) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("error", created.reason_code);
    return NextResponse.redirect(loginUrl, 303);
  }
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(IDENTITY_COOKIE_NAME, created.token, {
    httpOnly: true,
    secure: cookieSecure(request),
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
