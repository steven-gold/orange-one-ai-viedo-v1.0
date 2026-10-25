export type SocialAdapterProbe = {
  available: boolean;
  reason: string;
};

let adapterOverride: boolean | null = null;

export function bindSocialAdapterForTest(next: boolean | null): void {
  adapterOverride = next;
}

export function probeSocialAdapter(): SocialAdapterProbe {
  if (adapterOverride === true) return { available: true, reason: "" };
  return { available: false, reason: "SHARED_ADAPTER_UNAVAILABLE" };
}

export function acceptSocialDiscoveryIntent(): {
  status: "RUNNING" | "EXTERNAL_PENDING";
  blocker: string;
} {
  const probe = probeSocialAdapter();
  if (!probe.available) {
    return { status: "EXTERNAL_PENDING", blocker: probe.reason };
  }
  return { status: "RUNNING", blocker: "" };
}

export function acceptSocialPublishIntent(): {
  external: "PENDING_EXTERNAL";
  callback: string;
} {
  const probe = probeSocialAdapter();
  if (!probe.available) {
    return { external: "PENDING_EXTERNAL", callback: probe.reason };
  }
  return { external: "PENDING_EXTERNAL", callback: "ADAPTER_ACCEPTED" };
}
