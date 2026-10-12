import { LoginVisual } from "@/components/identity/LoginVisual";
import { isLoginReasonCode } from "@/server/domain/identity";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; email?: string }>;
}) {
  const params = await searchParams;
  const error = typeof params.error === "string" && isLoginReasonCode(params.error) ? params.error : "";
  const email = typeof params.email === "string" ? params.email : "";
  return <LoginVisual initialError={error} initialEmail={email} />;
}
