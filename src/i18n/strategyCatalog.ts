import type { Locale } from "./catalog";

type StrategyLabel = { tw: string; en: string };

const STRATEGY_LABELS: readonly [string, string, string][] = [
  ["STR-01-FLD-TOPIC", "Strategy Topic", "Strategy Topic"],
  ["STR-01-FLD-SCOPE", "Strategy Scope", "Strategy Scope"],
  ["STR-01-FLD-HORIZON", "Time Horizon", "Time Horizon"],
  ["STR-01-FLD-STATE", "Strategy State", "Strategy State"],
  ["STR-01-FLD-DECISION-STATE", "Decision Status", "Decision Status"],
  ["STR-01-TGL-MODE", "Single AI / Multi AI", "Single AI / Multi AI"],
  ["STR-01-INP-TOPIC-SEARCH", "搜尋策略議題", "Search strategy topics"],
  ["STR-01-LST-TOPICS", "Strategy Topics / History", "Strategy Topics / History"],
  ["STR-01-LST-CONTEXT", "Strategic Context Sources", "Strategic Context Sources"],
  ["STR-01-FLD-CONTEXT-PRIORITY", "Context Priority", "Context Priority"],
  ["STR-01-FLD-CONTEXT-SOURCE", "Source / Ref", "Source / Ref"],
  ["STR-01-FLD-CONTEXT-TIME", "Source Time / Version", "Source Time / Version"],
  ["STR-01-FLD-CONTEXT-CONFIDENCE", "Confidence / Quality", "Confidence / Quality"],
  ["STR-01-LST-ALERTS", "Strategy Alerts / Open Questions", "Strategy Alerts / Open Questions"],
  ["STR-01-VIEW-CONVERSATION", "Strategic AI Conversation", "Strategic AI Conversation"],
  ["STR-01-BTN-ATTACH", "附件 / 圖片", "Attachment / Image"],
  ["STR-01-INP-MESSAGE", "輸入策略議題、問題或分析要求", "Enter strategy issue, question, or analysis request"],
  ["STR-01-BTN-SEND", "送出", "Send"],
  ["STR-01-BTN-STOP", "停止生成", "Stop generation"],
  ["STR-01-FLD-ASSISTANT-SUMMARY", "Assistant Summary", "Assistant Summary"],
  ["STR-01-FLD-OPEN-QUESTIONS", "Open Questions", "Open Questions"],
  ["STR-01-FLD-MEETING-RECORD", "Meeting / Discussion Record", "Meeting / Discussion Record"],
  ["STR-01-FLD-BASIS", "分析依據 / Basis", "Analysis Basis"],
  ["STR-01-FLD-ASSUMPTIONS", "假設 / Assumptions", "Assumptions"],
  ["STR-01-FLD-OPPORTUNITIES", "機會 / Opportunities", "Opportunities"],
  ["STR-01-FLD-RISKS", "風險 / Risks", "Risks"],
  ["STR-01-FLD-UNCERTAINTY", "不確定性 / Uncertainty", "Uncertainty"],
  ["STR-01-FLD-PATTERN", "Pattern / Baseline / Forecast", "Pattern / Baseline / Forecast"],
  ["STR-01-TBL-COMPARE", "Strategy Option Comparison", "Strategy Option Comparison"],
  ["STR-01-BTN-COMPARE", "比較方案", "Compare options"],
  ["STR-01-CARD-RECOMMENDATION", "Strategy Recommendation", "Strategy Recommendation"],
  ["STR-01-CARD-ALERT", "Strategy Alert", "Strategy Alert"],
  ["STR-01-CARD-RESOURCE", "Resource Proposal", "Resource Proposal"],
  ["STR-01-CARD-BRIEF", "Decision Brief", "Decision Brief"],
  ["STR-01-FLD-CANDIDATE-REF", "Strategy Candidate", "Strategy Candidate"],
  ["STR-01-FLD-REVIEW-STATE", "Review State", "Review State"],
  ["STR-01-FLD-DECISION-ID", "Decision ID", "Decision ID"],
  ["STR-01-FLD-DECISION-RESULT", "Decision Result", "Decision Result"],
  ["STR-01-FLD-DECISION-REASON", "Decision Reason", "Decision Reason"],
  ["STR-01-FLD-EXECUTION-STATE", "Execution Status / Ref", "Execution Status / Ref"],
  ["STR-01-BTN-SUBMIT-REVIEW", "送出策略審查", "Submit strategy review"],
  ["STR-01-BTN-ADOPT", "採用策略 Context", "Adopt Strategy Context"],
  ["STR-01-BTN-OPEN-OWNER", "開啟執行責任模組", "Open execution owner module"],
  ["STR-01-LST-PATTERNS", "Strategy Pattern / Cases", "Strategy Pattern / Cases"],
  ["STR-01-LST-EXPERIMENTS", "Experiment Records", "Experiment Records"],
  ["STR-01-LST-BASELINES", "Baseline History", "Baseline History"],
  ["STR-01-LST-LEARNING", "Learning Results", "Learning Results"],
  ["STR-01-FLD-EXPECTED", "Expected", "Expected"],
  ["STR-01-FLD-ACTUAL", "Actual", "Actual"],
  ["STR-01-FLD-DIFFERENCE", "Difference Analysis", "Difference Analysis"],
  ["STR-01-FLD-KPI", "KPI / Performance Change", "KPI / Performance Change"],
  ["STR-01-FLD-LEARNING", "Learning", "Learning"],
  ["STR-01-FLD-PROVIDER-BRAND", "Provider Brand", "Provider Brand"],
  ["STR-01-FLD-CORRELATION", "Correlation / Audit Ref", "Correlation / Audit Ref"],
  ["STR-01-FLD-DISABLED", "Disabled Reason", "Disabled Reason"],
  ["STR-01-FLD-OWNER-BOUNDARY", "Execution Owner Boundary", "Execution Owner Boundary"],
  ["STR-01-BTN-AUDIT", "查看 Audit / Trace", "View Audit / Trace"],
] as const;

export const STRATEGY_CONTROL_TEXT: Record<string, StrategyLabel> = Object.fromEntries(STRATEGY_LABELS.map(([id, tw, en]) => [id, { tw, en }]));
const REPLACEMENTS: readonly [string, string][] = [["搜尋","搜索"],["議題","议题"],["圖片","图片"],["輸入","输入"],["問題","问题"],["依據","依据"],["假設","假设"],["機會","机会"],["風險","风险"],["不確定性","不确定性"],["比較","比较"],["審查","审查"],["採用","采用"],["開啟","开启"],["執行","执行"],["責任","责任"],["模組","模块"]];
function toSimplified(input: string) { return REPLACEMENTS.reduce((v,[a,b]) => v.split(a).join(b), input); }
export function strategyText(locale: Locale, id: string) { const e=STRATEGY_CONTROL_TEXT[id]; if(!e) return id; if(locale==="en") return e.en; if(locale==="zh-CN") return toSimplified(e.tw); return e.tw; }

export const STRATEGY_UI_TEXT = {
  topics:{"zh-TW":"Strategy Topics / History","zh-CN":"Strategy Topics / History",en:"Strategy Topics / History"},
  context:{"zh-TW":"Strategic Context","zh-CN":"Strategic Context",en:"Strategic Context"},
  alerts:{"zh-TW":"Strategic Alerts / Open Questions","zh-CN":"Strategic Alerts / Open Questions",en:"Strategic Alerts / Open Questions"},
  conversation:{"zh-TW":"Strategic AI Conversation","zh-CN":"Strategic AI Conversation",en:"Strategic AI Conversation"},
  analysis:{"zh-TW":"Strategy Analysis","zh-CN":"Strategy Analysis",en:"Strategy Analysis"},
  compare:{"zh-TW":"Option Comparison","zh-CN":"Option Comparison",en:"Option Comparison"},
  outputs:{"zh-TW":"Strategy Outputs","zh-CN":"Strategy Outputs",en:"Strategy Outputs"},
  decision:{"zh-TW":"Human Review / Decision Ledger","zh-CN":"Human Review / Decision Ledger",en:"Human Review / Decision Ledger"},
  memory:{"zh-TW":"Strategic Memory / Experience","zh-CN":"Strategic Memory / Experience",en:"Strategic Memory / Experience"},
  feedback:{"zh-TW":"Feedback Loop","zh-CN":"Feedback Loop",en:"Feedback Loop"},
  status:{"zh-TW":"Audit / Boundary","zh-CN":"Audit / Boundary",en:"Audit / Boundary"},
  assistant:{"zh-TW":"Assistant Summary / Meeting Record","zh-CN":"Assistant Summary / Meeting Record",en:"Assistant Summary / Meeting Record"},
  mode:{"zh-TW":"Single / Multi AI Mode","zh-CN":"Single / Multi AI Mode",en:"Single / Multi AI Mode"},
  boundary:{"zh-TW":"策略中心只提供分析、提案與人工決策輔助；Finance / Workflow / Governance / Production 執行仍由責任模組負責。","zh-CN":"策略中心只提供分析、提案与人工决策辅助；Finance / Workflow / Governance / Production 执行仍由责任模块负责。",en:"Strategic Center provides analysis, proposals, and human decision support only. Finance, Workflow, Governance, and Production execution remain with their owning modules."}
} as const;
export type StrategyUiTextKey=keyof typeof STRATEGY_UI_TEXT;
export function strategyUiText(locale:Locale,key:StrategyUiTextKey){return STRATEGY_UI_TEXT[key][locale];}
