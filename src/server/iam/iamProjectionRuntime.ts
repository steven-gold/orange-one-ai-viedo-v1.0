import { cookies } from "next/headers";
import {
  IAM_ADMIN_L1_PAGE_UID,
  IAM_FRONT_L1_PAGE_UID,
} from "@/domain/iam/iamRuntimeContract";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import {
  CURRENT_PAGE_RESOURCE_KEYS,
  readCatalogPageProjection,
} from "@/server/shared/pageCatalogProjectionRuntime";

type Request = { page_uid: string; correlation_id: string };
type Row = Record<string, unknown>;

function record(value: unknown): Row | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : null;
}

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized || null;
}

function rows(value: unknown): Row[] {
  return Array.isArray(value)
    ? value.flatMap((item) => {
        const row = record(item);
        return row ? [row] : [];
      })
    : [];
}

function identitySource(externalSubject: unknown): string {
  const subject = text(externalSubject);
  if (!subject) return "UNBOUND";
  const separator = subject.indexOf(":");
  const source = (separator > 0 ? subject.slice(0, separator) : subject).trim();
  return source ? source.toUpperCase() : "UNBOUND";
}

const FRONT_RESOURCE_TO_L1 = new Map<string, string>(
  Object.entries(IAM_FRONT_L1_PAGE_UID).flatMap(([l1, pageUid]) => {
    const resourceKey = CURRENT_PAGE_RESOURCE_KEYS[pageUid];
    return resourceKey ? [[resourceKey, l1] as const] : [];
  }),
);
const ADMIN_RESOURCE_TO_L1 = new Map<string, string>(
  Object.entries(IAM_ADMIN_L1_PAGE_UID).flatMap(([l1, pageUid]) => {
    const resourceKey = CURRENT_PAGE_RESOURCE_KEYS[pageUid];
    return resourceKey ? [[resourceKey, l1] as const] : [];
  }),
);

export async function readProductionIamProjection(request: Request) {
  if (request.page_uid !== "admin:IAM-01") return null;

  const base = await readCatalogPageProjection(request);
  if (!base || !base.ok) return base;

  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) {
    return {
      ok: false as const,
      status: 503,
      reason_code: "DATABASE_RUNTIME_NOT_BOUND",
      correlation_id: request.correlation_id,
    };
  }

  let cookie: string | undefined;
  try {
    cookie = (await cookies()).get(IDENTITY_COOKIE_NAME)?.value;
  } catch {
    cookie = undefined;
  }
  const identity = await resolveIdentityFromCookie(cookie);
  if (!identity.ok || !cookie) {
    return {
      ok: false as const,
      status: identity.ok ? 401 : identity.status,
      reason_code: identity.ok ? "IDENTITY_RUNTIME_NOT_BOUND" : identity.reason_code,
      correlation_id: request.correlation_id,
    };
  }
  // Resolve the same canonical session context used by IAM command/runtime authorization.
  hashSessionToken(cookie);

  try {
    const [accountRowsRaw, assignmentRowsRaw, auditRowsRaw] = await Promise.all([
      sql`
        SELECT
          u.user_id::text AS account_id,
          u.display_name AS label,
          u.status::text AS status,
          u.email::text AS email,
          u.external_subject,
          a.id AS runtime_account_id,
          count(s.token_hash) FILTER (WHERE s.expires_at > now())::int AS active_session_count,
          max(s.expires_at) FILTER (WHERE s.expires_at > now())::text AS latest_active_session_expires_at
        FROM public.app_users u
        LEFT JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
        LEFT JOIN acpos_runtime.sessions s ON s.account_id=a.id
        WHERE u.disabled_at IS NULL
        GROUP BY u.user_id,u.display_name,u.status,u.email,u.external_subject,a.id
        ORDER BY u.created_at DESC
      `,
      sql`
        WITH effective AS (
          SELECT
            a.user_id::text AS account_id,
            r.resource_key,
            a.action,
            a.effect,
            row_number() OVER (
              PARTITION BY a.user_id,a.resource_id,a.action
              ORDER BY a.version_no DESC,a.effective_from DESC,a.account_permission_assignment_id DESC
            ) AS rn
          FROM public.account_permission_assignments a
          JOIN public.permission_resources r ON r.resource_id=a.resource_id
          WHERE a.status='APPROVED'
            AND a.effective_from<=now()
            AND (a.effective_to IS NULL OR a.effective_to>now())
            AND r.active=true
            AND r.resource_type='PAGE'
            AND a.action='VIEW'
        )
        SELECT account_id,resource_key
        FROM effective
        WHERE rn=1 AND effect='ALLOW'
        ORDER BY account_id,resource_key
      `,
      sql`
        SELECT action,reason,occurred_at::text AS occurred_at,correlation_id::text AS correlation_id
        FROM public.audit_events
        WHERE entity_type='admin:IAM-01'
        ORDER BY occurred_at DESC,audit_event_id DESC
        LIMIT 12
      `,
    ]);

    const frontByAccount = new Map<string, string[]>();
    const adminByAccount = new Map<string, string[]>();
    for (const row of rows(assignmentRowsRaw)) {
      const accountId = text(row.account_id);
      const resourceKey = text(row.resource_key);
      if (!accountId || !resourceKey) continue;
      const front = FRONT_RESOURCE_TO_L1.get(resourceKey);
      if (front) frontByAccount.set(accountId, [...(frontByAccount.get(accountId) ?? []), front]);
      const admin = ADMIN_RESOURCE_TO_L1.get(resourceKey);
      if (admin) adminByAccount.set(accountId, [...(adminByAccount.get(accountId) ?? []), admin]);
    }

    const accounts = rows(accountRowsRaw).flatMap((row) => {
      const accountId = text(row.account_id);
      const label = text(row.label);
      if (!accountId || !label) return [];
      const activeSessions = Math.max(0, Number(row.active_session_count ?? 0) || 0);
      return [{
        account_id: accountId,
        label,
        status: text(row.status) ?? "—",
        identity_source: identitySource(row.external_subject),
        organization_scope: "—",
        mfa: "—",
        risk: "—",
        session: `${activeSessions} ACTIVE SESSION${activeSessions === 1 ? "" : "S"}`,
        session_expires_at: text(row.latest_active_session_expires_at),
        front_l1: frontByAccount.get(accountId) ?? [],
        admin_l1: adminByAccount.get(accountId) ?? [],
        basic_data: { email: text(row.email) ?? "—" },
      }];
    });

    const auditEntries = rows(auditRowsRaw).map((row) => {
      const occurredAt = text(row.occurred_at) ?? "UNKNOWN_TIME";
      const action = text(row.action) ?? "UNKNOWN_ACTION";
      const reason = text(row.reason);
      const correlationId = text(row.correlation_id);
      return [occurredAt, action, reason, correlationId].filter(Boolean).join(" · ");
    });

    const value = record(base.value) ?? {};
    return {
      ...base,
      value: {
        ...value,
        authorized_account_count: accounts.length,
        accounts,
        audit_entries: auditEntries,
      },
    };
  } catch {
    return {
      ok: false as const,
      status: 503,
      reason_code: "IAM_PROJECTION_READ_FAILED",
      correlation_id: request.correlation_id,
    };
  }
}
