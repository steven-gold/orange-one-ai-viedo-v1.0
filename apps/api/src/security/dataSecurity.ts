const SENSITIVE_KEYS = ['password', 'token', 'secret', 'authorization', 'cookie'] as const;

/**
 * Outbound minimization: strip credentials from any payload that leaves the
 * navigation runtime so audit and response surfaces never carry secrets.
 */
export function redactSensitive<T extends Record<string, unknown>>(payload: T): Record<string, unknown> {
  const safe: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (SENSITIVE_KEYS.some((needle) => key.toLowerCase().includes(needle))) {
      safe[key] = '[REDACTED]';
      continue;
    }
    safe[key] = value;
  }
  return safe;
}
