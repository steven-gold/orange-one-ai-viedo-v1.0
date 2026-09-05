import { NextRequest, NextResponse } from "next/server";
import {
  IDENTITY_COOKIE_NAME,
  SESSION_TTL_SECONDS,
  createIdentitySession,
  destroyIdentitySession,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";

export const dynamic = "force-dynamic";

function correlationId(request: NextRequest): string {
  const supplied = request.headers.get("x-correlation-id")?.trim();
  return supplied || crypto.randomUUID();
}

function json(
  body: unknown,
  status: number,
  correlation_id: string,
): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
      "x-correlation-id": correlation_id,
    },
  });
}

function cookieSecure(request: NextRequest): boolean {
  return request.nextUrl.protocol === "https:" || process.env.ACPOS_DEPLOYMENT_ENV === "production";
}

function applySessionCookie(response: NextResponse, request: NextRequest, token: string | null) {
  if (!token) {
    response.cookies.set(IDENTITY_COOKIE_NAME, "", {
      httpOnly: true,
      secure: cookieSecure(request),
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return;
  }
  response.cookies.set(IDENTITY_COOKIE_NAME, token, {
    httpOnly: true,
    secure: cookieSecure(request),
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
}

export async function GET(request: NextRequest) {
  const correlation_id = correlationId(request);
  const resolved = await resolveIdentityFromCookie(request.cookies.get(IDENTITY_COOKIE_NAME)?.value);
  if (!resolved.ok) {
    return json(
      { ok: false, logged_in: false, reason_code: resolved.reason_code, correlation_id },
      resolved.status,
      correlation_id,
    );
  }
  return json(
    {
      ok: true,
      logged_in: true,
      display_name: resolved.actor.display_name,
      email: resolved.actor.email,
      correlation_id,
    },
    200,
    correlation_id,
  );
}

export async function POST(request: NextRequest) {
  const correlation_id = correlationId(request);
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return json({ ok: false, reason_code: "INVALID_JSON_PAYLOAD", correlation_id }, 400, correlation_id);
  }
  const record = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const email = typeof record.email === "string" ? record.email : "";
  const password = typeof record.password === "string" ? record.password : "";
  const created = await createIdentitySession(email, password);
  if (!created.ok) {
    return json({ ok: false, reason_code: created.reason_code, correlation_id }, created.status, correlation_id);
  }
  const response = json(
    {
      ok: true,
      logged_in: true,
      display_name: created.actor.display_name,
      email: created.actor.email,
      correlation_id,
    },
    200,
    correlation_id,
  );
  applySessionCookie(response, request, created.token);
  return response;
}

export async function DELETE(request: NextRequest) {
  const correlation_id = correlationId(request);
  await destroyIdentitySession(request.cookies.get(IDENTITY_COOKIE_NAME)?.value);
  const response = json({ ok: true, logged_in: false, correlation_id }, 200, correlation_id);
  applySessionCookie(response, request, null);
  return response;
}
