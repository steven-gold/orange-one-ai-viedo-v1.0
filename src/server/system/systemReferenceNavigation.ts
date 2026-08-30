export type SystemReferenceNavigationRequest = {
  system_change_id: string;
  reference_ref: string;
};

export type SystemReferenceNavigationBinding = {
  resolve: (request: SystemReferenceNavigationRequest) => Promise<{ ok: true; href: string } | { ok: false; reason_code: string }>;
};

let binding: SystemReferenceNavigationBinding | null = null;

export function configureSystemReferenceNavigation(next: SystemReferenceNavigationBinding): void {
  binding = next;
}

export async function resolveSystemReferenceNavigation(request: SystemReferenceNavigationRequest) {
  if (!binding) return { ok: false as const, reason_code: "SYSTEM_REFERENCE_NAVIGATION_NOT_BOUND" };
  return binding.resolve(request).catch(() => ({ ok: false as const, reason_code: "SYSTEM_REFERENCE_NAVIGATION_FAILED" }));
}
