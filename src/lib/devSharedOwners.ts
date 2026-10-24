export type SharedOwnerProbe = {
  available: boolean;
  reason: string;
};

let acquisitionBound = true;
let deliveryBound = true;

export function bindSharedOwnersForTest(next: { acquisition?: boolean; delivery?: boolean } | null): void {
  if (next === null) {
    acquisitionBound = true;
    deliveryBound = true;
    return;
  }
  if (typeof next.acquisition === "boolean") acquisitionBound = next.acquisition;
  if (typeof next.delivery === "boolean") deliveryBound = next.delivery;
}

export function probeSharedAcquisition(): SharedOwnerProbe {
  return acquisitionBound
    ? { available: true, reason: "" }
    : { available: false, reason: "SHARED_ACQUISITION_UNAVAILABLE" };
}

export function probeSharedDelivery(): SharedOwnerProbe {
  return deliveryBound
    ? { available: true, reason: "" }
    : { available: false, reason: "SHARED_DELIVERY_UNAVAILABLE" };
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
