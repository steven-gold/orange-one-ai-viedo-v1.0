import type { Locale } from "./catalog";

type QaLabel = { tw: string; en: string };

const QA_LABELS: readonly [string, string, string][] = [
  ["QA-01-FLD-PROJECT", "Project", "Project"],
  ["QA-01-FLD-TOPIC", "Topic", "Topic"],
  ["QA-01-FLD-QA-TASK", "QA Task", "QA Task"],
  ["QA-01-FLD-TARGET-OUTPUT", "Target Output Version", "Target Output Version"],
  ["QA-01-FLD-REVIEW-STATE", "QA Review State", "QA Review State"],
  ["QA-01-BTN-START-REVIEW", "開始審查", "Start Review"],
  ["QA-01-INP-QUEUE-SEARCH", "搜尋 QA Task / Output / Finding", "Search QA Task / Output / Finding"],
  ["QA-01-SEL-QUEUE-STATE", "狀態篩選", "State Filter"],
  ["QA-01-SEL-QUEUE-SEVERITY", "Severity", "Severity"],
  ["QA-01-LIST-REVIEWS", "QA Review Queue", "QA Review Queue"],
  ["QA-01-SEG-REVIEW-MODE", "審查模式", "Review Mode"],
  ["QA-01-BTN-AUTO-START", "開始自動審查", "Start AUTO Review"],
  ["QA-01-FLD-AUTO-PROGRESS", "AUTO Progress", "AUTO Progress"],
  ["QA-01-SEL-QUEUE-SOURCE-DEPT", "來源部門", "Source Department"],
  ["QA-01-VIEW-OUTPUT", "Exact Output Viewer", "Exact Output Viewer"],
  ["QA-01-BTN-PLAY", "Play / Pause", "Play / Pause"],
  ["QA-01-CTL-SEEK", "Seek / Timecode", "Seek / Timecode"],
  ["QA-01-BTN-VOLUME", "Volume / Mute", "Volume / Mute"],
  ["QA-01-BTN-FULLSCREEN", "Fullscreen", "Fullscreen"],
  ["QA-01-BTN-COMPARE", "Before / After Compare", "Before / After Compare"],
  ["QA-01-BTN-PREV-FRAME", "上一幀", "Previous Frame"],
  ["QA-01-BTN-NEXT-FRAME", "下一幀", "Next Frame"],
  ["QA-01-FLD-CURRENT-TIMECODE", "Current Timecode", "Current Timecode"],
  ["QA-01-BTN-FINDING-POINT", "標記 Finding 位置", "Set Finding Point"],
  ["QA-01-BTN-EVIDENCE-IN", "Evidence In", "Evidence In"],
  ["QA-01-BTN-EVIDENCE-OUT", "Evidence Out", "Evidence Out"],
  ["QA-01-FLD-QA-SCRIPT", "QA Validation Script View", "QA Validation Script View"],
  ["QA-01-FLD-SCRIPT-HASH", "Script View Hash", "Script View Hash"],
  ["QA-01-FLD-CRITERIA-VERSION", "Criteria Version", "Criteria Version"],
  ["QA-01-FLD-GATE-POLICY", "Quality Gate Policy Version", "Quality Gate Policy Version"],
  ["QA-01-BTN-SCRIPT-VIEW", "查看 QA 驗證腳本", "View QA Validation Script"],
  ["QA-01-FLD-EVIDENCE", "Evidence Refs", "Evidence Refs"],
  ["QA-01-FLD-CHECKSUM", "Artifact Checksum", "Artifact Checksum"],
  ["QA-01-FLD-PROVENANCE", "Provenance", "Provenance"],
  ["QA-01-FLD-REQUIRED-CHECKS", "Required Checks", "Required Checks"],
  ["QA-01-FLD-RIGHTS", "Rights Gate", "Rights Gate"],
  ["QA-01-FLD-POLICY", "Policy Gate", "Policy Gate"],
  ["QA-01-BTN-EVIDENCE", "查看 Evidence / Checks", "View Evidence / Checks"],
  ["QA-01-FLD-TOTAL-SCORE", "Total Score", "Total Score"],
  ["QA-01-FLD-HARD-BLOCK", "Hard Block", "Hard Block"],
  ["QA-01-FLD-GATE-STATUS", "QA Gate Result", "QA Gate Result"],
  ["QA-01-FLD-OPEN-FINDINGS", "Open Blocking Findings", "Open Blocking Findings"],
  ["QA-01-FLD-MANUAL-STATE", "Manual Review", "Manual Review"],
  ["QA-01-LIST-SCORE-DIMENSIONS", "Generated Criteria Dimensions", "Generated Criteria Dimensions"],
  ["QA-01-LIST-FINDINGS", "Finding List", "Finding List"],
  ["QA-01-INP-FINDING-SEVERITY", "Severity（registered enum）", "Severity (registered enum)"],
  ["QA-01-INP-FINDING-CATEGORY", "Category（registered QA issue category）", "Category (registered QA issue category)"],
  ["QA-01-INP-FINDING-SCOPE", "Affected Scope", "Affected Scope"],
  ["QA-01-INP-FINDING-EVIDENCE", "Evidence Refs（auto-bound）", "Evidence Refs (auto-bound)"],
  ["QA-01-BTN-FINDING-CREATE", "建立 Finding", "Create Finding"],
  ["QA-01-FLD-MANUAL-CASE", "Manual Review Case", "Manual Review Case"],
  ["QA-01-FLD-MANUAL-OWNER", "Owner", "Owner"],
  ["QA-01-FLD-MANUAL-BLOCKER", "Blocking Reason", "Blocking Reason"],
  ["QA-01-FLD-MANUAL-DECISION", "Decision / History", "Decision / History"],
  ["QA-01-BTN-MANUAL-VIEW", "查看人工審查", "View Manual Review"],
  ["QA-01-BTN-MANUAL-MODIFY", "修改", "Modify"],
  ["QA-01-BTN-MANUAL-PASS", "通過", "Pass"],
  ["QA-01-INP-CORR-FINDINGS", "Finding IDs", "Finding IDs"],
  ["QA-01-INP-CORR-SCORECARDS", "Source Scorecard IDs", "Source Scorecard IDs"],
  ["QA-01-INP-CORR-INSTRUCTION", "Source Instruction Package", "Source Instruction Package"],
  ["QA-01-INP-CORR-SCOPE", "Affected Scope", "Affected Scope"],
  ["QA-01-INP-CORR-ROOT", "Root Cause（canonical enum）", "Root Cause (canonical enum)"],
  ["QA-01-INP-CORR-ACTION", "Required Action", "Required Action"],
  ["QA-01-INP-CORR-TARGET", "Target Department / Original Owner", "Target Department / Original Owner"],
  ["QA-01-INP-CORR-REVALIDATE", "Revalidation Requirements", "Revalidation Requirements"],
  ["QA-01-BTN-CORRECTION", "要求修正", "Request Correction"],
  ["QA-01-FLD-FAILED-VERSION", "Failed Output Version", "Failed Output Version"],
  ["QA-01-FLD-NEW-VERSION", "Verified New Output Version", "Verified New Output Version"],
  ["QA-01-FLD-RECHECK-STATUS", "Recheck Status", "Recheck Status"],
  ["QA-01-BTN-RECHECK", "開始 Recheck", "Start Recheck"],
  ["QA-01-FLD-REL-QA-PASS", "QA PASS", "QA PASS"],
  ["QA-01-FLD-REL-FINDINGS", "All Findings Closed", "All Findings Closed"],
  ["QA-01-FLD-REL-MANUAL", "Manual Review Closed", "Manual Review Closed"],
  ["QA-01-FLD-REL-RIGHTS", "Rights Valid", "Rights Valid"],
  ["QA-01-FLD-REL-POLICY", "Policy Valid", "Policy Valid"],
  ["QA-01-FLD-REL-CHANNEL", "Channel / Account Scope", "Channel / Account Scope"],
  ["QA-01-FLD-REL-PACKAGE", "Release Package Candidate", "Release Package Candidate"],
  ["QA-01-FLD-REL-OUTPUTS", "Exact Output Version IDs", "Exact Output Version IDs"],
  ["QA-01-FLD-REL-QA-GATE", "QA Gate Ref", "QA Gate Ref"],
  ["QA-01-FLD-REL-RIGHTS-GATE", "Rights Gate Ref", "Rights Gate Ref"],
  ["QA-01-BTN-RELEASE-CREATE", "建立 Release Candidate", "Create Release Candidate"],
  ["QA-01-FLD-PAGE-STATE", "Page / QA State", "Page / QA State"],
  ["QA-01-FLD-ERROR", "Error UID / Reason", "Error UID / Reason"],
  ["QA-01-FLD-DISABLED", "Disabled Reason", "Disabled Reason"],
  ["QA-01-FLD-CORRELATION", "Correlation / Idempotency", "Correlation / Idempotency"],
  ["QA-01-FLD-AUDIT", "Audit / Trace", "Audit / Trace"],
  ["QA-01-BTN-AUDIT", "查看 Audit / Trace", "View Audit / Trace"],
] as const;

export const QA_CONTROL_TEXT: Record<string, QaLabel> = Object.fromEntries(
  QA_LABELS.map(([id, tw, en]) => [id, { tw, en }]),
);

const REPLACEMENTS: readonly [string, string][] = [
  ["審查", "审查"], ["搜尋", "搜索"], ["狀態", "状态"], ["篩選", "筛选"], ["來源", "来源"], ["部門", "部门"],
  ["上一幀", "上一帧"], ["下一幀", "下一帧"], ["標記", "标记"], ["驗證", "验证"], ["腳本", "脚本"],
  ["建立", "创建"], ["人工", "人工"], ["通過", "通过"], ["開始", "开始"], ["錯誤", "错误"], ["關聯", "关联"],
];

function toSimplified(input: string) {
  return REPLACEMENTS.reduce((value, [from, to]) => value.split(from).join(to), input);
}

export function qaText(locale: Locale, id: string) {
  const entry = QA_CONTROL_TEXT[id];
  if (!entry) return id;
  if (locale === "en") return entry.en;
  if (locale === "zh-CN") return toSimplified(entry.tw);
  return entry.tw;
}

export const QA_UI_TEXT = {
  queue: { "zh-TW": "QA Review Queue", "zh-CN": "QA Review Queue", en: "QA Review Queue" },
  viewer: { "zh-TW": "Exact Output Viewer", "zh-CN": "Exact Output Viewer", en: "Exact Output Viewer" },
  scriptCriteria: { "zh-TW": "QA 驗證腳本 / 評分規範", "zh-CN": "QA 验证脚本 / 评分规范", en: "QA Validation Script / Criteria" },
  evidence: { "zh-TW": "Evidence / Required Checks", "zh-CN": "Evidence / Required Checks", en: "Evidence / Required Checks" },
  scoreGate: { "zh-TW": "System / AI Scorecard / QA Gate", "zh-CN": "System / AI Scorecard / QA Gate", en: "System / AI Scorecard / QA Gate" },
  finding: { "zh-TW": "Finding List", "zh-CN": "Finding List", en: "Finding List" },
  findingDetail: { "zh-TW": "Finding 建立 / 詳細資料", "zh-CN": "Finding 创建 / 详细资料", en: "Finding Create / Detail" },
  manual: { "zh-TW": "Manual Review", "zh-CN": "Manual Review", en: "Manual Review" },
  correction: { "zh-TW": "Correction Request", "zh-CN": "Correction Request", en: "Correction Request" },
  recheck: { "zh-TW": "Verified New Version / Recheck", "zh-CN": "Verified New Version / Recheck", en: "Verified New Version / Recheck" },
  releaseReady: { "zh-TW": "Release Eligibility", "zh-CN": "Release Eligibility", en: "Release Eligibility" },
  release: { "zh-TW": "Release Candidate / Package", "zh-CN": "Release Candidate / Package", en: "Release Candidate / Package" },
  audit: { "zh-TW": "Status / Error / Audit", "zh-CN": "Status / Error / Audit", en: "Status / Error / Audit" },
  noReview: { "zh-TW": "目前沒有可顯示的 QA Review", "zh-CN": "目前没有可显示的 QA Review", en: "No QA review available" },
  noOutput: { "zh-TW": "尚未解析 Exact Output", "zh-CN": "尚未解析 Exact Output", en: "Exact output is not resolved" },
  scoreReadonly: { "zh-TW": "Scorecard 由 System / AI 產生；此區沒有人工評分或 PASS / FAIL 按鈕。", "zh-CN": "Scorecard 由 System / AI 产生；此区没有人工评分或 PASS / FAIL 按钮。", en: "Scorecard is generated by System / AI. No human scoring or PASS / FAIL action exists here." },
} as const;

export type QaUiTextKey = keyof typeof QA_UI_TEXT;
export function qaUiText(locale: Locale, key: QaUiTextKey) { return QA_UI_TEXT[key][locale]; }
