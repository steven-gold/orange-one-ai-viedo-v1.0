---
document_id: CHANGE-CORE-001
canonical_name: CORE_01_CONVERSATION_WORKSPACE_REDESIGN
entity_type: CHANGE
page_uid: CORE-01
change_level: LEVEL_4_PAGE_REDESIGN
status: DRAFT_FOR_VISUAL_REVIEW
branch: new
source_revision: 5d5ead002104870a942e2658aeacc7e3618baa73
created_date: 2026-09-11
owner_scope: CORE-01 existing canonical owner only
creates_second_authority: false
implementation_allowed_before_visual_approval: false
---

# CORE-01 對話工作區重新審查與更新規劃

## 0. 文件定位

本文件是 `CORE-01` 的正式 Change Planning Unit，用於重新審查既有頁面資訊架構、AI 對話整合、欄位／按鈕／狀態綁定與全站視覺一致性。

本文件 **不是第二份 CORE Authority**，也 **不直接取代** 現有：

- `authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml`
- `authority/global/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY_FINAL_LOCKED.yaml`
- `authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml`

在 Visual Preview、Visual Review、Visual Approval 完成前：

- MUST_NOT 修改正式 CORE-01 Runtime Contract。
- MUST_NOT 直接把本文件標示為新的 Current Authority。
- MUST_NOT 以本文件繞過原有 Canonical Owner。
- MUST_NOT 建立第二套 CORE page、第二套 conversation runtime、第二套 control identity。

Visual Approval 後，應更新 **既有 CORE-01 Canonical Owner**，再由 Implementation 依更新後 Owner 施工。

---

## 1. Current Truth 與審查來源

### 1.1 Current Source

- Branch: `new`
- Revision: `5d5ead002104870a942e2658aeacc7e3618baa73`
- Page route: `/core`
- Page UID: `CORE-01`

### 1.2 Current Canonical / Implementation Owners Reviewed

1. `authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml`
2. `authority/global/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY_FINAL_LOCKED.yaml`
3. `src/app/core/page.tsx`
4. `src/components/pages/CoreVisual.tsx`
5. `src/components/pages/CoreVisual.module.css`
6. `src/app/globals.css`
7. `CURRENT_EXECUTION_STATE.json`

### 1.3 Change Classification

本次屬：

`LEVEL_4_PAGE_REDESIGN`

理由：

- 不重做 Global Shell。
- 不改 Navigation Authority。
- 不改品牌色方向。
- 不建立新的 AI conversation runtime。
- 需要重新整理 CORE-01 的 Page-level Information Architecture、Section Relationship、Control Presentation、Field Gate 與 Visual Binding。

---

## 2. 審查結論

### 2.1 問題不是單純 CSS 跑版

Current CORE Authority 將中心工作區拆成：

1. `CORE-01-SEC-03` Conversation Header
2. `CORE-01-SEC-04` Message Workspace
3. `CORE-01-SEC-05` Evaluation / Human Decision
4. `CORE-01-SEC-06` Runtime Stage Strip
5. `CORE-01-SEC-07` Input Composer

其中 `SEC-03 + SEC-04 + SEC-06 + SEC-07` 在使用者體驗上其實同屬一個 AI Conversation Workspace，但目前被視覺拆成多張卡片，造成：

- AI 模式與訊息流分離。
- 對話內容與輸入 Composer 分離。
- Runtime Status 像額外功能，不像對話狀態。
- Attachment / Reference 與實際輸入上下文缺乏可見綁定。
- 使用者感受不到「目前這一個 Thread 的 AI、訊息、輸入、狀態是一個完整工作單位」。

### 2.2 Current Authority 與 Current CSS 幾何偏差

Current Authority 定義：

- Left Rail min width: `260px`
- Center min width: `720px`
- Right Rail min width: `300px`
- Approx ratio: `20% / 60% / 20%`

Current `CoreVisual.module.css` 實際使用較小基礎：

- Left: `minmax(190px, .85fr)`
- Center: `minmax(0, 2.8fr)`
- Right: `minmax(220px, 1fr)`

此偏差會壓縮真正需要最高資訊密度的 AI conversation area。

### 2.3 AI Mode 有功能，缺 Selected Visual Binding

現有：

- `CORE-01-BTN-SINGLE-AI`
- `CORE-01-BTN-MULTI-AI`

已具 action，但 UI 目前是兩顆普通 compact button。

Global Visual Authority 已定義：

- `selected conversation mode` 必須使用 selected violet semantics。

因此新版 MUST 顯示：

- Current selected mode。
- Inactive mode。
- Disabled reason（如 Multi AI route 尚未 ready）。

### 2.4 Message Role 沒有使用 Global Message Surface

Global Visual Authority 已存在：

- `surface.message_user`
- `surface.message_ai`
- `surface.message_assistant`

但 Current CORE message rendering 使用同一 `readonlyField` 表現 User / AI / Assistant / System。

結果：

- Message role hierarchy 不清楚。
- User input 與 AI output 視覺語意相同。
- Assistant structured role 不可辨識。

新版 MUST 使用既有 Global Message Surface，不新增 Page-local palette。

### 2.5 Human Decision UI Gate 與 Authority Flow 未完全一致

Current Authority 定義：

`AI_RESPONSES -> ASSISTANT_SUMMARY -> CORE_EVALUATION -> HUMAN_DECISION -> ASSISTANT_STRUCTURED_DECISION -> CANDIDATE_CREATE -> CANDIDATE_DECISION`

Current frontend 的 Human Decision textarea 主要依 `conversation_id` 啟用。

新版 MUST 對齊：

- Summary Ready
- Evaluation Ready
- Exact current context/thread
- No stale candidate/context

未滿足時 Human Decision 保持 Disabled 並顯示 exact disabled reason。

### 2.6 Candidate Create 的 UX Gate 必須完整反映正式 Gate

新版 `CORE-01-BTN-CANDIDATE-CREATE` 的 UI availability MUST 顯示以下必要條件：

- Active exact conversation thread
- Assistant Summary Ready
- CORE Evaluation Ready
- Human Decision non-empty
- Structured Decision Ready
- Required evidence/source refs ready

Runtime 仍以正式 backend contract 為最終 Enforcement；UI 只做可見、可理解的同源 Gate 表現。

### 2.7 Attachment / Reference 缺乏可見 Context Binding

現有控制：

- `CORE-01-BTN-ATTACHMENT`
- `CORE-01-BTN-REFERENCE`

Current local state 已保存 refs，但 Composer 沒有充分顯示「目前掛了哪些資源」。

新版 Composer MUST 顯示：

- attachment chips / rows
- reference chips / rows
- exact count
- removable state（只有當既有 runtime/client state contract允許時）
- disabled reason

不得顯示虛構檔名、假資料或不存在的 business label。

### 2.8 Runtime Stage 不應成為獨立視覺卡片

Current `CORE-01-SEC-06` 是獨立 40px strip。

新版視覺應把 Runtime Stage 視為 Conversation Workspace 狀態的一部分：

- Toolbar Status；或
- Composer Status Line。

保留原 `CORE-01-SEC-06` / `CORE-01-CMP-RUNTIME` identity，直到 Design Change Approval 決定是否正式 merge section owner；在 Approval 前不得自行刪 UID。

### 2.9 Right-click Message Menu 位置需要修正

Current menu 以 Message Workspace 中央定位。

新版 MUST：

- Anchor 到被操作 message 的 pointer / message row vicinity。
- 不遮蔽整個 Conversation Workspace 中央。
- 保留既有 message action identity。
- Keyboard / focus path 必須可操作。

### 2.10 Page-local Control Styling 過多

Current CORE 自行定義：

- `.button`
- `.primaryButton`
- `.compactButton`
- `.selectField`
- `.textareaField`
- `.readonlyField`

雖然有引用 Global tokens，但仍形成 Page-local control presentation implementation。

更新方向：

`GLOBAL TOKEN -> SHARED CONTROL VARIANT -> PAGE BINDING`

而非：

`GLOBAL TOKEN -> EACH PAGE RECREATES BUTTON/FIELD CSS`

本 Change 不要求立刻重構全站；但 CORE-01 新版不得新增第二套 button/input palette 或 state semantics。

---

## 3. 新版資訊架構

### 3.1 Top Context Bar — 保留

Owner：`CORE-01-SEC-01`

用途：

- Project select
- Project create
- Topic select
- Topic create
- Page Mode
- Naming Authority

規則：

- 只處理全頁 Context。
- 不放 AI provider/model picker。
- 不放 Conversation-local action。

### 3.2 Left Rail — 保留但改善資訊層級

Owner：`CORE-01-SEC-02`

內容順序：

1. Current Work Item selector
2. Conversation Thread header
3. New Thread
4. Thread List

要求：

- Selected Work Item 必須使用 Global selected semantics。
- Selected Thread 必須清楚可辨識。
- Thread item 顯示內容不得由前端虛構。
- Thread list > 520px 才 internal scroll。

### 3.3 Center — AI Conversation Workspace（核心更新）

視覺上整合既有：

- `CORE-01-SEC-03`
- `CORE-01-SEC-04`
- `CORE-01-SEC-06`
- `CORE-01-SEC-07`

成為 **一個連續 Conversation Workspace Container**。

#### A. Conversation Toolbar

必須包含：

- Current Work Item
- Current Thread context
- Single AI / Multi AI segmented control
- Assigned AI Set read-only
- Assistant Record toggle/action
- Runtime / responding / blocked state indicator

#### B. Message Stream

必須包含：

- User message
- AI message
- Assistant message
- System / Status message
- Context right-click menu
- Loading / Responding state
- Empty state
- Error state

Message Visual Binding：

- USER -> Global `message_user`
- AI / SIMULATED_AI -> Global `message_ai`
- ASSISTANT -> Global `message_assistant`
- SYSTEM / STATUS -> neutral/status semantic based on actual state

不得發明新的 role color theme。

#### C. Composer Context Tray

位置：Message Stream 下方、Input Composer 上方。

顯示：

- Active attachment refs
- Active reference refs
- Mention/context state where resolvable
- Disabled/block reason

#### D. Composer

必須形成單一操作列：

`Attachment | Reference | Message Textarea | Send`

要求：

- Composer 永遠屬於目前 active Thread。
- 無 Thread 時整體 Disabled。
- Send 只在 message non-empty + exact thread + route/gate ready 時可用。
- Busy 時維持 geometry，不得 layout jump。

### 3.4 Center — Decision Workspace（保留為下一生命週期）

Owner：`CORE-01-SEC-05`

位置：Conversation Workspace 下方。

順序：

1. Assistant Summary
2. CORE Evaluation
3. Human Decision
4. Structured Decision
5. Candidate Create
6. Candidate Confirm / Return Modify

Field Gate：

- Summary：read-only
- Evaluation：read-only
- Human Decision：Summary + Evaluation Ready 才 Enabled
- Structured Decision：read-only
- Candidate Create：全部 required sources ready 才 Enabled
- Candidate Confirm / Return：exact Candidate ref ready 才 Enabled

### 3.5 Right Rail — 保留正式狀態與 Review Action

保留：

- `CORE-01-SEC-08`
- `CORE-01-SEC-09`
- `CORE-01-SEC-10`

Right Rail 不承擔 Conversation Composer 或一般 AI mode control。

內容：

- Project Core State
- Blueprint State
- Topic Production Package
- Downstream readiness
- Candidate / Version Compare
- Lock Review State

高風險／正式 review actions 必須繼續使用既有 Gate、permission、runtime contract。

---

## 4. Layout 更新規格

### 4.1 Desktop Base

- Page min width: `1280px`
- Page vertical: `auto`, Main Workspace scrollable
- Context Bar height: `56px`
- Main Grid gap: `16px`

### 4.2 Primary Grid

恢復 Current Authority 基準：

- Left: `minmax(260px, 1fr)`
- Center: `minmax(720px, 3fr)`
- Right: `minmax(300px, 1fr)`

Priority：

`CENTER CONVERSATION > LEFT NAV > RIGHT STATUS`

### 4.3 Center Conversation Container

建議：

- min-height: `620px`
- Toolbar: `56–72px`
- Message viewport: `min-height 420px`
- Context tray: content-height
- Composer: `min-height 104px`

不得為了固定一屏高度把 message、decision、composer 壓縮成不可用尺寸。

### 4.4 Width Below Minimum

Current Authority 規則保留：

- min-width remains `1280px`
- allow horizontal scroll
- MUST_NOT 發明 mobile parallel workflow

---

## 5. Global Design Binding

### 5.1 色彩

只能使用 Global Visual Authority：

- Page: `#050816`
- Surface L1: `#0C1026`
- Surface L2: `#111936`
- Input: `#0A0F24`
- Popup: `#0B1027`
- Primary Purple: `#8B5CFF`
- Secondary Purple: `#6E35FF`
- Highlight Purple: `#B38CFF`

### 5.2 Control Geometry

- Normal control height: `40px`
- Compact control height: `32px`
- Button radius: `10px`
- Panel radius: `12px`
- Section gap: `16px`
- Inner gap: `12px`
- Content padding: `16px`

### 5.3 Button Binding

Existing CORE controls MUST bind to：

- Primary
- Secondary
- Selected
- Disabled
- Danger（only formally destructive/reject action）

Page-local new button theme = FORBIDDEN。

### 5.4 Field Binding

Text / Select / Textarea / Readonly MUST inherit Global base semantics。

Page may own：

- exact width
- grid placement
- label
- permission state
- visibility
- domain state

Page MUST_NOT own a second palette/state language。

---

## 6. Existing Control Identity Preservation

本次 redesign 預設保留所有已註冊 CORE control identity，不得因重排視覺重新命名。

至少包含：

- `CORE-01-CTL-PROJECT`
- `CORE-01-BTN-PROJECT-CREATE`
- `CORE-01-CTL-TOPIC`
- `CORE-01-BTN-TOPIC-CREATE`
- `CORE-01-LST-WORK-ITEMS`
- `CORE-01-BTN-NEW-THREAD`
- `CORE-01-LST-THREADS`
- `CORE-01-BTN-SINGLE-AI`
- `CORE-01-BTN-MULTI-AI`
- `CORE-01-FLD-ASSIGNED-AI`
- `CORE-01-BTN-ASSISTANT-RECORD`
- `CORE-01-FLD-ASSISTANT-SUMMARY`
- `CORE-01-FLD-EVALUATION`
- `CORE-01-FLD-HUMAN-DECISION`
- `CORE-01-FLD-STRUCTURED-DECISION`
- `CORE-01-BTN-CANDIDATE-CREATE`
- `CORE-01-BTN-CANDIDATE-CONFIRM`
- `CORE-01-BTN-RETURN-MODIFY`
- `CORE-01-FLD-RUNTIME-STAGE`
- `CORE-01-BTN-ATTACHMENT`
- `CORE-01-BTN-REFERENCE`
- `CORE-01-FLD-MESSAGE`
- `CORE-01-BTN-SEND`

以及既有 Project / Story / DNA / Blueprint / Version / Lock controls。

規則：

`REPOSITION != RENAME`

`VISUAL MERGE != CONTRACT MERGE`

只有正式 Authority Change 明確決議後才可 merge/remove Section / Component UID。

---

## 7. AI Conversation Binding 規範

### 7.1 Same Context Rule

Single AI / Multi AI 必須共享：

- same Project
- same Topic（if applicable）
- same Work Item
- same Thread context
- same Attachment refs
- same Reference refs

切換 AI Mode 不得另開第二套 message history。

### 7.2 Assigned AI

- Read-only
- 由 shared AI Router / Capability Assignment 決定
- Page 不得提供 Provider picker
- Page 不得提供 Model picker

### 7.3 Message + Composer Binding

Message Stream、Composer、Attachment、Reference、Send、Runtime Status 必須在同一 Conversation Workspace 中有明確 Parent Relationship。

### 7.4 Message Action Menu

保留既有：

- Quote
- Continue
- Analyze
- Decision List
- Branch
- Copy

Context Menu MUST anchor to exact selected message ref。

---

## 8. State / Disabled Reason 規範

所有 effectful controls MUST：

- 可追溯 exact action uid
- 可追溯 permission / gate
- Disabled 時提供 exact disabled reason
- Busy 時保留 geometry
- Error 時顯示 real error，不顯示 fake success

Conversation Workspace 至少呈現：

- EMPTY
- READY
- RESPONDING
- EVALUATING
- WAIT_HUMAN_DECISION
- CANDIDATE_READY
- REVIEW_PENDING
- LOCKED
- ERROR / BLOCKED

---

## 9. Change Impact Set

受影響 Owner / Implementation：

### Design / Authority

- `authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml`
- Global visual remains referenced; no palette redesign planned

### Frontend

- `src/components/pages/CoreVisual.tsx`
- `src/components/pages/CoreVisual.module.css`

### Shared presentation verification

- `src/app/globals.css`

### Localization

- Existing CORE keys MUST be reused where semantically correct
- New copy MAY be added only after exact missing key audit
- Brand / ACPOS / AI / API / QA fixed term rules remain

### Tests / Evidence

Affected CORE visual/frontend/control acceptance items MUST become:

`REVERIFY_REQUIRED`

---

## 10. Visual Preview Gate — 強制

Implementation 前 MUST 先完成：

1. 依本文件產生 `CORE-01` 新版實際網站畫面預覽。
2. 預覽必須使用 Current Global Shell / Global Visual tokens。
3. 預覽必須顯示：
   - Context Bar
   - Left Work Item / Threads
   - Integrated AI Conversation Workspace
   - Decision Workspace
   - Right Status Rail
4. 必須至少呈現以下狀態：
   - Thread selected / ready
   - Single AI selected
   - Multi AI disabled or selected state example based on exact data state
   - User / AI / Assistant message role distinction
   - Attachment / Reference context tray
   - Human Decision disabled-before-ready
   - Human Decision enabled-after-ready
5. Visual Review 只修改 Change Set 指定範圍。
6. 未取得 `VISUAL_APPROVED`，MUST_NOT 進 Frontend Implementation。

---

## 11. Acceptance Matrix（Design Change）

| Audit Item | Requirement | PASS Condition |
|---|---|---|
| CHANGE-CORE-001-AUD-01 | Single Canonical Owner | 無第二 CORE page / owner |
| CHANGE-CORE-001-AUD-02 | Conversation Integration | Header + Messages + Runtime + Composer 視覺形成單一 Workspace |
| CHANGE-CORE-001-AUD-03 | AI Mode Binding | Single/Multi selected state 可辨識，與 current state 同步 |
| CHANGE-CORE-001-AUD-04 | Message Role Visual | User/AI/Assistant 使用 Global role surfaces |
| CHANGE-CORE-001-AUD-05 | Composer Binding | Message / Attachment / Reference / Send 同一 conversation context |
| CHANGE-CORE-001-AUD-06 | Decision Gate | Human Decision 只在 Summary + Evaluation ready 時可用 |
| CHANGE-CORE-001-AUD-07 | Candidate Gate | Candidate Create 可見條件與 required source/gate 一致 |
| CHANGE-CORE-001-AUD-08 | Layout Fidelity | 260 / 720 / 300 minimum layout restored |
| CHANGE-CORE-001-AUD-09 | Global Visual | 無 page-local second palette / button theme |
| CHANGE-CORE-001-AUD-10 | Context Menu | Menu anchored to selected message context |
| CHANGE-CORE-001-AUD-11 | i18n | zh-TW / zh-CN / en 無 raw key / overflow regression |
| CHANGE-CORE-001-AUD-12 | Visual Preview | 新版 Preview 完成 |
| CHANGE-CORE-001-AUD-13 | Visual Approval | Authorized review = VISUAL_APPROVED |
| CHANGE-CORE-001-AUD-14 | Reverify Scope | 受影響舊 PASS 已標 REVERIFY_REQUIRED |

---

## 12. Definition of Done — 本 Change Planning Unit

本更新規劃檔可標示 `PLANNING_CLOSED` 的條件：

- Current CORE Authority 已重新審查。
- Current CORE implementation 已重新審查。
- Layout / AI Conversation / Control / Field / Visual gaps 已列出。
- 新版 Information Architecture 已定義。
- Existing Control Identity preservation 已定義。
- Global Design binding 已定義。
- Visual Preview Gate 已定義。
- Acceptance Matrix 已定義。

但 `CHANGE-CORE-001` 本身 **不得** 因 Planning Closed 宣稱：

- CORE-01 已修改完成。
- Visual 已批准。
- Frontend 已施工。
- Tests 已 PASS。
- Production 已更新。

---

## 13. 後續固定執行順序

`CHANGE REVIEW`
→ `UPDATED CORE PAGE DESIGN SPEC`
→ `CONTROL / FIELD / STATE BINDING`
→ `GENERATION MANIFEST`
→ `VISUAL PREVIEW`
→ `VISUAL REVIEW`
→ `VISUAL_APPROVED`
→ `UPDATE EXISTING CORE AUTHORITY OWNER`
→ `FRONTEND IMPLEMENTATION`
→ `CONTROL / GATE REVERIFY`
→ `VISUAL REGRESSION`
→ `BROWSER ACCEPTANCE`
→ `PRODUCTION ACCEPTANCE WHEN RELEASED`

禁止：

`PLAN -> DIRECT CODE CHANGE -> LATER FIX AUTHORITY`

---

## 14. Current Status

- Review: `COMPLETED_FOR_PLANNING`
- Change Plan: `CREATED`
- Visual Preview: `NOT_EXECUTED`
- Visual Approval: `NOT_EXECUTED`
- Authority Update: `NOT_EXECUTED`
- Frontend Implementation: `NOT_EXECUTED`
- Test / Reverify: `NOT_EXECUTED`
- Deployment: `NOT_EXECUTED`

Exact next action：

`Generate the CORE-01 updated visual preview from CHANGE-CORE-001 without modifying production implementation.`
