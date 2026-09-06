export class NamedRuntimeError extends Error {
  readonly reason_code: string;

  constructor(reason_code: string) {
    super(reason_code);
    this.name = "NamedRuntimeError";
    this.reason_code = reason_code;
  }
}

export function namedReason(error: unknown, fallback: string): string {
  if (error instanceof NamedRuntimeError) return error.reason_code;
  if (error instanceof Error && error.name === "NamedRuntimeError" && /^[A-Z][A-Z0-9_:]{2,120}$/.test(error.message)) {
    return error.message;
  }
  return fallback;
}
