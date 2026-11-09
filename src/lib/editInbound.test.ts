import assert from "node:assert/strict";
import { test } from "node:test";
import { resolveEditInbound } from "./editInbound";

const manifest = {
  kind: "EXACT_VIDEO_HANDOFF_MANIFEST",
  manifest_id: "VHM-1",
  checksum: "VCKS-65207d16",
  output_uri: "acpos://video/ACPOS-VIDEO-v1",
};

test("handoffContract keeps full manifest JSON intact (evidence chain)", () => {
  const video = (uid: string) =>
    uid === "VIDEO-01-FLD-PROJECT" ? "P1" :
    uid === "VIDEO-01-FLD-TOPIC" ? "T1" :
    uid === "VIDEO-01-FLD-HANDOFF-CONTRACT" ? JSON.stringify(manifest) : null;
  const inbound = resolveEditInbound(video, () => null, () => null);
  assert.equal(inbound.handoffContract, JSON.stringify(manifest));
});

test("handoffContract falls back to raw JSON when checksum is missing", () => {
  const video = (uid: string) =>
    uid === "VIDEO-01-FLD-PROJECT" ? "P1" :
    uid === "VIDEO-01-FLD-TOPIC" ? "T1" :
    uid === "VIDEO-01-FLD-HANDOFF-CONTRACT" ? JSON.stringify({ kind: "EXACT_VIDEO_HANDOFF_MANIFEST" }) : null;
  const inbound = resolveEditInbound(video, () => null, () => null);
  assert.equal(inbound.handoffContract, '{"kind":"EXACT_VIDEO_HANDOFF_MANIFEST"}');
});

test("handoffContract keeps exact names intact for non-JSON handoffs", () => {
  const video = (uid: string) =>
    uid === "VIDEO-01-FLD-PROJECT" ? "P1" :
    uid === "VIDEO-01-FLD-TOPIC" ? "T1" :
    uid === "VIDEO-01-FLD-HANDOFF-CONTRACT" ? "VCKS-legacy" : null;
  const inbound = resolveEditInbound(video, () => null, () => null);
  assert.equal(inbound.handoffContract, "VCKS-legacy");
});
