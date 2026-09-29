import { NextRequest, NextResponse } from "next/server";
import {
  IDENTITY_COOKIE_NAME,
  SESSION_TTL_SECONDS,
  createIdentitySession,
} from "@/server/identity/identityRuntime";

function firstHeader(request: NextRequest, name: string): string {
  return (request.headers.get(name) ?? "").split(",")[0].trim();
}

function seeOther(path: string): NextResponse {
  return new NextResponse(null, {
    status: 303,
    headers: { Location: path },
  });
}

function cookieSecure(request: NextRequest): boolean {
  return (
    request.nextUrl.protocol === "https:" ||
    firstHeader(request, "x-forwarded-proto") === "https" ||
    process.env.ACPOS_DEPLOYMENT_ENV === "production"
  );
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "");
  const password = String(form.get("password") ?? "");
  const created = await createIdentitySession(email, password);
  if (!created.ok) {
    return seeOther(`/login?error=${encodeURIComponent(created.reason_code)}`);
  }
  const response = seeOther("/");
  response.cookies.set(IDENTITY_COOKIE_NAME, created.token, {
    httpOnly: true,
    secure: cookieSecure(request),
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
