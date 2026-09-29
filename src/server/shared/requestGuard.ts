type RateBucket = { window_started_at: number; count: number; last_seen_at: number };

export type RateLimitDecision = {
  allowed: boolean;
  limit: number;
  remaining: number;
  retry_after_seconds: number;
};

const buckets = new Map<string, RateBucket>();
const DEFAULT_LIMIT = 120;
const DEFAULT_WINDOW_MS = 60_000;
const MAX_BUCKETS = 10_000;

function positiveInteger(raw: string | undefined, fallback: number) {
  if (!raw) return fallback;
  const value = Number.parseInt(raw, 10);
  return Number.isSafeInteger(value) && value > 0 ? value : fallback;
}

function config() {
  return {
    limit: positiveInteger(process.env.ACPOS_RATE_LIMIT_MAX, DEFAULT_LIMIT),
    window_ms: positiveInteger(process.env.ACPOS_RATE_LIMIT_WINDOW_MS, DEFAULT_WINDOW_MS),
  };
}

function prune(now: number, windowMs: number) {
  for (const [key, bucket] of buckets) {
    if (now - bucket.last_seen_at >= windowMs) buckets.delete(key);
  }
  if (buckets.size <= MAX_BUCKETS) return;
  const overflow = buckets.size - MAX_BUCKETS;
  const oldest = [...buckets.entries()]
    .sort((left, right) => left[1].last_seen_at - right[1].last_seen_at)
    .slice(0, overflow);
  for (const [key] of oldest) buckets.delete(key);
}

export function clientIdentity(headers: Headers) {
  const forwarded = headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const realIp = headers.get("x-real-ip")?.trim();
  return forwarded || realIp || "unresolved-client";
}

export function checkMutationRateLimit(identity: string, now = Date.now()): RateLimitDecision {
  const { limit, window_ms } = config();
  prune(now, window_ms);

  const existing = buckets.get(identity);
  const bucket = !existing || now - existing.window_started_at >= window_ms
    ? { window_started_at: now, count: 0, last_seen_at: now }
    : existing;

  bucket.count += 1;
  bucket.last_seen_at = now;
  buckets.set(identity, bucket);

  const allowed = bucket.count <= limit;
  const remaining = Math.max(0, limit - bucket.count);
  const retryAfterMs = Math.max(0, window_ms - (now - bucket.window_started_at));

  return {
    allowed,
    limit,
    remaining,
    retry_after_seconds: allowed ? 0 : Math.max(1, Math.ceil(retryAfterMs / 1000)),
  };
}
