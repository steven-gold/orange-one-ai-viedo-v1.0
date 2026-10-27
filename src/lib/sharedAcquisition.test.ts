import {
  parsePublicCompanyRows,
  parseGcisCompanyRows,
  parseGcisBusinessItems,
  mergeDiscoverySignals,
  expandTokenFamily,
  searchTokensOf,
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
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
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
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
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
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
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
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
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

{
  const gcisSource = "SRC-GCIS-COMPANY-KEYWORD";
  const gcisRows = [
    {
      Business_Accounting_NO: "16540340",
      Company_Name: "曄拓保養品股份有限公司",
      Company_Status: "01",
      Company_Status_Desc: "核准設立",
      Capital_Stock_Amount: 470000000,
      Register_Organization: "21",
      Register_Organization_Desc: "臺南市政府",
      Company_Location: "臺南市安南區科技三路1號",
    },
    {
      Business_Accounting_NO: "16540340",
      Company_Name: "曄拓保養品股份有限公司（重複）",
      Company_Status_Desc: "核准設立",
    },
  ];
  const profile: DevProfile = {
    profileId: "PRF-GCIS",
    version: 1,
    product: "保養品",
    industry: "",
    market: "",
    keywords: "保養品",
    exclude: "",
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
    mode: "SINGLE",
    status: "ACTIVE",
  };
  const signals = parseGcisCompanyRows(gcisRows, profile, gcisSource);
  assert(signals.length === 1, "gcis rows dedupe by registration number");
  assert(signals[0].identityValue === "TW-16540340", "gcis tax id becomes registration identity");
  assert(signals[0].address === "臺南市安南區科技三路1號", "gcis registered address is copied onto the signal");
  assert(signals[0].evidence.includes("經濟部商業發展署公司登記資料"), "gcis evidence carries the source name");
}

{
  const family = expandTokenFamily("保養品");
  assert(family.includes("化粧品") && family.includes("美容") && family.includes("清潔用品"), "skincare token expands to cosmetics family");
  const profile: DevProfile = {
    profileId: "PRF-TOK",
    version: 1,
    product: "保養品",
    industry: "",
    market: "",
    keywords: "",
    exclude: "",
    language: "zh-TW",
    priority: "NORMAL",
    sourceScope: "ALLOWED",
    mode: "SINGLE",
    status: "ACTIVE",
  };
  const tokens = searchTokensOf(profile);
  assert(!tokens.includes("zh-TW"), "language codes never become search tokens");
  assert(tokens.includes("保養品") && tokens.includes("化粧品"), "search tokens include the product word and its family");
}

{
  const items = parseGcisBusinessItems([
    {
      Business_Accounting_NO: "16540340",
      Cmp_Business: [
        { Business_Item: "C802100", Business_Item_Desc: "化粧品製造業" },
        { Business_Item: "F108040", Business_Item_Desc: "化粧品批發業" },
      ],
    },
  ]);
  assert(items.length === 1 && items[0].identityValue === "TW-16540340", "business items keep registration identity");
  assert(items[0].items.join("、") === "化粧品製造業、化粧品批發業", "business items keep item descriptions");
}

{
  const existing: DevSignal[] = [
    {
      signalId: "SIG-GCIS",
      companyName: "曄拓保養品股份有限公司",
      intent: "保養品",
      evidence: "經濟部商業發展署公司登記資料 16540340",
      freshness: "2026-10-27",
      identityKind: "REGISTRATION",
      identityValue: "TW-16540340",
      match: "resolved",
      opportunity: "OPEN",
      status: "NEW",
      version: 1,
      address: "臺南市安南區科技三路1號",
    },
  ];
  const incoming: DevSignal[] = [
    {
      signalId: "SIG-TWSE",
      companyName: "曄拓保養品股份有限公司",
      intent: "保養品",
      evidence: "臺灣證券交易所上市基本資料 4763",
      freshness: "2026-10-27",
      identityKind: "REGISTRATION",
      identityValue: "TW-16540340",
      match: "resolved",
      opportunity: "OPEN",
      status: "NEW",
      version: 1,
      email: "service@example.com",
      phone: "06-0000000",
    },
  ];
  const merged = mergeDiscoverySignals(existing, incoming);
  assert(merged.length === 1, "cross-source merge keeps one signal per registration identity");
  const filled = merged[0];
  assert(filled.email === "service@example.com", "cross-source merge fills email from the later source");
  assert(filled.phone === "06-0000000", "cross-source merge fills phone from the later source");
  assert(filled.address === "臺南市安南區科技三路1號", "cross-source merge keeps the earlier address");
  assert(filled.evidence.includes("經濟部") && filled.evidence.includes("證券交易所"), "cross-source merge keeps both evidence strings");
}

console.log("sharedAcquisition.test.ts PASS");
