export type SharedOwnerProbe = {
  available: boolean;
  reason: string;
};

let acquisitionOverride: boolean | null = null;
let deliveryOverride: boolean | null = null;

export function bindSharedOwnersForTest(next: { acquisition?: boolean; delivery?: boolean } | null): void {
  if (next === null) {
    acquisitionOverride = null;
    deliveryOverride = null;
    return;
  }
  if (typeof next.acquisition === "boolean") acquisitionOverride = next.acquisition;
  if (typeof next.delivery === "boolean") deliveryOverride = next.delivery;
}

export function probeSharedAcquisition(): SharedOwnerProbe {
  if (acquisitionOverride === false) return { available: false, reason: "SHARED_ACQUISITION_UNAVAILABLE" };
  if (acquisitionOverride === true) return { available: true, reason: "" };
  return { available: true, reason: "" };
}

export function probeSharedDelivery(): SharedOwnerProbe {
  if (deliveryOverride === true) return { available: true, reason: "" };
  return { available: false, reason: "SHARED_DELIVERY_UNAVAILABLE" };
}

export function acceptDiscoveryIntent(): {
  status: "RUNNING" | "EXTERNAL_PENDING";
  blocker: string;
} {
  const probe = probeSharedAcquisition();
  if (!probe.available) {
    return { status: "EXTERNAL_PENDING", blocker: probe.reason };
  }
  return { status: "RUNNING", blocker: "" };
}

export function acceptDeliveryIntent(): {
  status: "QUEUED" | "EXTERNAL_PENDING";
  result: string;
} {
  const probe = probeSharedDelivery();
  if (!probe.available) {
    return { status: "EXTERNAL_PENDING", result: "EXTERNAL_PENDING" };
  }
  return { status: "QUEUED", result: "QUEUED" };
}
