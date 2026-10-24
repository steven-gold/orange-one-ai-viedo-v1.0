import {
  parsePublicCompanyRows,
  mergeDiscoverySignals,
  PUBLIC_JSON_SOURCES,
} from "./sharedAcquisition";
import type { DevProfile, DevSignal } from "./devState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

const source = PUBLIC_JSON_SOURCES[0];
const rows = [
  { 公司代號: "2330", 公司名稱: "台灣積體電路製造股份有限公司", 產業別: "半導體業", 營利事業統一編號: "16131121", 電子郵件: "invest@tsmc.com", 總機電話: "03-5636688" },
  { 公司代號: "6184", 公司名稱: "大豐有線電視股份有限公司", 產業別: "文化創意業", 營利事業統一編號: "97179431", 電子郵件信箱: "service@tfctv.com.tw", 總機電話: "02-00000000", 住址: "新北市" },
  { 公司代號: "9917", 公司名稱: "中華電視股份有限公司", 產業別: "文化創意業", 營利事業統一編號: "03793901" },
];

{
  const profile: DevProfile = {
    profileId: "PRF-1",
    version: 1,
    product: "影像工作臺",
    industry: "文化創意",
    market: "",
    keywords: "電視",
    exclude: "",
    mode: "SINGLE",
    status: "ACTIVE",
  };
  const signals = parsePublicCompanyRows(rows, profile, source);
  assert(signals.length === 2, "culture/tv tokens match listed media companies");
  assert(signals.every((item) => item.identityKind === "REGISTRATION"), "signals keep registration identity");
  assert(signals.every((item) => item.status === "NEW"), "collected signals start NEW");
  assert(!signals.some((item) => item.companyName.includes("台灣積體")), "unrelated semiconductor is excluded");
  const cable = signals.find((item) => item.identityValue === "TW-97179431");
  assert(cable?.email === "service@tfctv.com.tw", "public email is copied onto the signal");
  assert(cable?.phone === "02-00000000", "public phone is copied onto the signal");
}

{
  const profile: DevProfile = {
    profileId: "PRF-2",
    version: 1,
    product: "影像工作臺",
    industry: "半導體",
    market: "",
    keywords: "",
    exclude: "有線",
    mode: "SINGLE",
    status: "ACTIVE",
  };
  const signals = parsePublicCompanyRows(rows, profile, source);
  assert(signals.length === 1, "exclude token drops matching names");
  assert(signals[0].identityValue === "TW-16131121", "tax id becomes registration identity");
}

{
  const existing: DevSignal[] = [
    {
      signalId: "SIG-OLD",
      companyName: "中華電視股份有限公司",
      intent: "採購",
      evidence: "舊證據",
      freshness: "2026-01-01",
      identityKind: "REGISTRATION",
      identityValue: "TW-03793901",
      match: "resolved",
      opportunity: "OPEN",
      status: "QUALIFIED",
      version: 2,
    },
  ];
  const incoming = parsePublicCompanyRows(rows, {
    profileId: "PRF-3",
    version: 1,
    product: "",
    industry: "媒體",
    market: "",
    keywords: "",
    exclude: "",
    mode: "SINGLE",
    status: "ACTIVE",
  }, source);
  const merged = mergeDiscoverySignals(existing, incoming);
  const kept = merged.find((item) => item.identityValue === "TW-03793901");
  assert(kept?.status === "QUALIFIED", "merge keeps decided signal");
  assert(merged.length === 2, "merge adds unseen identities only");
}

{
  const existing: DevSignal[] = [
    {
      signalId: "SIG-NEW",
      companyName: "大豐有線電視股份有限公司",
      intent: "採購",
      evidence: "舊證據",
      freshness: "2026-01-01",
      identityKind: "REGISTRATION",
      identityValue: "TW-97179431",
      match: "resolved",
      opportunity: "OPEN",
      status: "NEW",
      version: 1,
    },
  ];
  const incoming = parsePublicCompanyRows(rows, {
    profileId: "PRF-4",
    version: 1,
    product: "",
    industry: "媒體",
    market: "",
    keywords: "",
    exclude: "",
    mode: "SINGLE",
    status: "ACTIVE",
  }, source);
  const merged = mergeDiscoverySignals(existing, incoming);
  const filled = merged.find((item) => item.identityValue === "TW-97179431");
  assert(filled?.status === "NEW", "recollect keeps NEW status");
  assert(filled?.signalId === "SIG-NEW", "recollect keeps the existing signal id");
  assert(filled?.email === "service@tfctv.com.tw", "recollect fills public email onto NEW signals");
  assert(filled?.phone === "02-00000000", "recollect fills public phone onto NEW signals");
}

console.log("sharedAcquisition.test.ts PASS");
