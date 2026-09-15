---
document_id: WEB-GOV-01
version: 2.1.0
order: 1
category: blueprint_design_governance
required_before_execution: true
status: normative
permanent_inheritance: true
---

# 01 基礎藍圖、視覺設計、命名與檔案治理規範

<!-- SECTION_UID: WEB-GOV-01-S000 -->
## 0. 規範目的

本文件定義網站或資訊系統在正式施工前必須完成的基礎藍圖、命名、設計、視覺確認、檔案治理與驗收基準。

本文件為施工前強制規範。未完成本文件要求之必要 Gate，不得進入正式 Implementation。

<!-- SECTION_UID: WEB-GOV-01-S001 -->
## 1. 規範關鍵字

- `MUST`：強制要求，不得省略。
- `MUST_NOT`：禁止事項。
- `SHOULD`：原則上應執行；若不執行，必須記錄理由。
- `MAY`：可選項目。
- `REQUIRED`：該項為驗收必要條件。
- `OPTIONAL`：該項非必要條件。
- `NOT_APPLICABLE`：經正式判定不適用。

<!-- SECTION_UID: WEB-GOV-01-S002 -->
## 2. 最高治理原則

系統 MUST 遵守：

- ONE AUTHORITY
- ONE CONCEPT
- ONE CANONICAL NAME
- ONE CANONICAL UID
- ONE OWNER FILE
- ONE DESIGN SOURCE
- ONE CURRENT CANONICAL VISUAL
- ONE IMPLEMENTATION OWNER
- ONE RUNTIME PATH
- ONE PRODUCTION TRUTH

任何正式項目 MUST 可由唯一 UID、Canonical Name 與 Owner File 追溯。

<!-- SECTION_UID: WEB-GOV-01-S003 -->
## 3. 文件讀取順序

AI MUST 依下列順序讀取規範：

1. `01_BLUEPRINT_DESIGN_GOVERNANCE.md`
2. `02_IMPLEMENTATION_DELIVERY_STANDARD.md`
3. `03_EXECUTION_CONTROL_STANDARD.md`
4. `04_AUDIT_PROGRESS_STANDARD.md`

後位文件不得推翻前位文件之 Authority、Naming、Design Freeze 或 Scope。

<!-- SECTION_UID: WEB-GOV-01-S003A -->
## 3A. 永久繼承與後續變更治理

本四份規範自專案採用後，MUST 對所有後續生命週期永久有效，包括：

- 新增功能
- 修改既有功能
- 修復缺陷
- 重構
- 設計調整
- 資料模型調整
- 權限調整
- 外部整合調整
- 測試補強
- 部署
- 回滾
- 維護
- 版本升級

本四份規範 MUST_NOT 僅被視為初始化或第一次施工規範。

每一個 Change Request 開始前 MUST：

1. 解析受影響 Canonical UID。
2. 找到現有 Canonical Owner。
3. 解析受影響的 Design、Contract、Runtime、Database、Permission、Test 與 Audit Items。
4. 執行 Naming Guard、Duplicate Guard、Owner Guard、Second-System Guard 與 Classification Guard。
5. 判定是修改既有 Governed Unit，或建立真正新的 Governed Unit。
6. 建立 Change Impact Set。
7. 只修改受影響 Canonical Owners。
8. 更新所有必要 Reference。
9. 將受影響的既有 PASS Audit Item 轉為 `REVERIFY_REQUIRED`。
10. 重新驗證後才允許恢復 PASS。

既有 Canonical Owner 存在時，MUST 修改原 Owner，MUST_NOT 以平行新檔繞過治理。

只有在完整搜尋後確認不存在既有 Governed Unit，且新內容具有獨立治理生命週期時，才 MAY 建立新的 Canonical Owner。

永久規則：

- `UPDATE MUST FOLLOW EXISTING CANONICAL OWNERSHIP`
- `CHANGE DOES NOT CREATE A SECOND AUTHORITY`
- `MODIFY THE OWNER; DO NOT CREATE A PARALLEL COPY`
- `REVERIFY AFFECTED PASS ITEMS AFTER EVERY MATERIAL CHANGE`

<!-- SECTION_UID: WEB-GOV-01-S004 -->
## 4. Authority 分層

正式資料 MUST 分離為：

- Authority：定義系統是什麼。
- Architecture：定義系統如何組成與依賴。
- Design：定義系統長什麼樣與如何互動。
- Contract：定義各層如何串接。
- Implementation：定義真正執行程式。
- Evidence：證明實作、測試、部署與正式驗收結果。

MUST_NOT 讓 Generated Content、測試報告、建置輸出或部署紀錄反向成為產品 Authority。

<!-- SECTION_UID: WEB-GOV-01-S005 -->
## 5. Canonical Naming Authority

系統 MUST 建立唯一 Naming Registry。

每一正式項目 MUST 具備：

- UID
- Entity Type
- Canonical Name
- Display Name
- Code Name
- Canonical File Name
- Module UID
- Parent UID
- Aliases
- Deprecated Names
- Owner File
- Version
- Status

同一概念 MUST_NOT 使用多個 Canonical Name。

Aliases 只能用於搜尋與歷史相容，MUST_NOT 成為第二正式名稱。

<!-- SECTION_UID: WEB-GOV-01-S006 -->
## 6. 命名格式

<!-- SECTION_UID: WEB-GOV-01-S006-01 -->
### 6.1 Canonical Name

機器識別名稱 MUST 使用：

`UPPER_SNAKE_CASE`

<!-- SECTION_UID: WEB-GOV-01-S006-02 -->
### 6.2 UID 統一格式

UID MUST 使用：

`{TYPE_PREFIX}-{SCOPE}-{SEQUENCE}`

TYPE_PREFIX MUST 從正式 Registry 選用，至少包括：

- `MOD`
- `PAGE`
- `SEC`
- `COMP`
- `CTRL`
- `FIELD`
- `ACTION`
- `API`
- `RUNTIME`
- `DB`
- `TABLE`
- `PERM`
- `ROLE`
- `ASSET`
- `VISUAL`
- `GEN`
- `CHANGE`
- `TEST`
- `EVID`
- `FLOW`
- `STATE`
- `LAYOUT`
- `AUDIT`

同一 Entity Type MUST 使用同一 UID 規則。

<!-- SECTION_UID: WEB-GOV-01-S006-03 -->
### 6.3 檔名格式

正式治理檔案 MUST 使用：

`{UID}_{CANONICAL_NAME}.{extension}`

MUST_NOT 使用以下版本式或模糊命名：

- `new`
- `final`
- `latest`
- `fixed`
- `backup`
- `copy`
- `v2`、`v3` 等未經正式版本制度管理的尾碼

版本 MUST 由 Version Metadata 與 Source Control 管理，不得靠複製檔案管理。

Candidate governance registries restored before Formal Freeze MAY retain an already-established fixed canonical filename only when all of the following are registered and machine-validated: exact `UID`, `Canonical Name`, `Canonical File Name`, `Canonical Path`, `Owner File`, `Version`, and `filename_exception_authority: WEB-GOV-01-S006-03`. This exception is limited to `GOVERNANCE_REGISTRY` / `GOVERNANCE_BLUEPRINT` current artifacts, MUST_NOT apply to program artifacts, and MUST_NOT permit version-like, backup, copy, temp, old, fuzzy, or alternate filenames. A future rename MUST use the governed Rename Procedure and migrate every forward/reverse reference atomically.

<!-- SECTION_UID: WEB-GOV-01-S007 -->
## 7. Rename Procedure

Canonical Name 或 File Name 需要變更時 MUST：

1. 建立正式 Rename Change。
2. 確認舊 UID 與新名稱。
3. UID 原則上保持不變；若 UID 必須變更，需建立 Mapping。
4. 更新 Naming Registry。
5. 舊名稱加入 Deprecated Names。
6. 更新所有 Reference。
7. 更新 Owner File Name。
8. 更新 Contract Reference。
9. 更新 Code Reference。
10. 更新 Tests。
11. 執行 Broken Reference Audit。
12. 確認無第二套名稱後完成。

MUST_NOT 只改單一檔名或單一程式符號。

<!-- SECTION_UID: WEB-GOV-01-S008 -->
## 8. 搜尋規範

AI 在判定項目不存在前 MUST 依序搜尋：

1. Canonical UID
2. Canonical Name
3. Alias
4. Deprecated Name
5. Registry
6. Owner Path
7. Related Code Symbol
8. Route / Endpoint / Data Object Reference

第一次搜尋沒有結果 MUST_NOT 直接建立新項目。

<!-- SECTION_UID: WEB-GOV-01-S009 -->
## 9. Atomic Owner File 原則

具有獨立治理生命週期的項目 MUST 具有唯一 Owner File。

獨立治理生命週期判斷包括：

- 可獨立修改
- 可獨立批准
- 可獨立封板
- 可獨立版本化
- 可被其他單位引用
- 可具有獨立 Runtime
- 可具有獨立 Test
- 可具有獨立 Asset
- 可具有獨立狀態

普通、僅存在於單一上層單位且無獨立生命週期的細項 SHOULD 歸屬最近的 Owner File，避免過度碎檔。

<!-- SECTION_UID: WEB-GOV-01-S010 -->
## 10. Registry 與 Owner File 分離

Registry MUST 只保存索引欄位：

- UID
- Canonical Name
- Owner File
- Parent
- Version
- Status
- Dependency Summary

Registry MUST_NOT 複製完整正式內容形成第二 Authority。

<!-- SECTION_UID: WEB-GOV-01-S011 -->
## 11. 專案根目錄標準分類

專案 SHOULD 採固定分類：

```text
00_AUTHORITY/
01_ARCHITECTURE/
02_DESIGN/
03_CONTRACTS/
04_APP/
05_RUNTIME/
06_DATABASE/
07_INTEGRATIONS/
08_SECURITY/
09_TESTS/
10_OPS/
11_EVIDENCE/
12_DOCS/
archive/
```

同一類型 MUST 使用唯一正式資料夾名稱。

MUST_NOT 同時存在多個意義相同但名稱不同的資料夾。

<!-- SECTION_UID: WEB-GOV-01-S011A -->
## 11A. 分類、去重、內容切割與零殘留治理

正式分類 MUST 以治理責任為基礎，不得以複製完整內容到多個資料夾代替分類。

必須遵守：

- `ONE GOVERNED UNIT = ONE CANONICAL OWNER`
- `REFERENCE, DO NOT COPY`
- `NO DUPLICATE PAYLOAD`
- `NO SECOND AUTHORITY`
- `NO UNJUSTIFIED RESIDUAL FILES`

### Content Bloat Guard

分類前後 MUST 檢查：

- Exact Duplicate Payload
- Semantic Duplicate
- Duplicate Owner
- Duplicate UID
- Duplicate Canonical Name
- Duplicate Runtime
- Duplicate API
- Duplicate Permission
- Duplicate Data Truth
- Duplicate Design Authority
- Duplicate Audit Authority

同一正式內容若需被不同分類使用，SHOULD 由其他位置以 UID、Owner Path、Version 與 Status Reference 指向 Canonical Owner，不得保存完整正文副本。

### Mixed Responsibility File Guard

大型檔案若同時包含多個具有獨立治理生命週期的責任，MUST 標示並處理：

- `SPLIT_REQUIRED`
- `MIXED_ALLOWED`

`MIXED_ALLOWED` 必須記錄具體理由，證明其內容共享同一 Owner、Lifecycle、Approval、Version 與 Runtime/Testing Scope。

治理切分粒度 MUST 以責任語義為準，不得以 YAML/JSON/Markdown/DOM/資料夾/檔案等語法或容器層級直接視為最終治理單元。任何仍包含多個獨立 Owner、Lifecycle、Approval、Version、Test/Acceptance Scope 或 Stage Identity 的 Terminal Unit MUST 標記 `SPLIT_REQUIRED` 並遞迴拆分；只有完整 `MIXED_ALLOWED` 證據才可例外。

MUST_NOT 為了拆檔而過度碎片化普通 Page-local 或 Parent-local 細項。

### Source-to-Target Traceability

重新分類或切割時 MUST 建立可追溯 Mapping，至少包含：

- Source Path
- Source UID
- Canonical Target Owner
- Canonical Target Path
- Split Status
- Split Targets
- References Created
- Removed Duplicate
- Preservation Status
- Evidence Reference

必要條件：

- `UNMAPPED_REQUIRED_CONTENT = 0`
- `LOST_REQUIRED_CONTENT = 0`
- `BROKEN_REFERENCE = 0`

### Zero Residual Rule

治理完成後 MUST 清除所有無正當用途的：

- Duplicate
- Temporary
- Backup
- Copy
- Abandoned Split Artifact
- Unused Reference
- Dead Owner
- Dead Contract
- Dead Runtime
- Dead Test
- Empty Placeholder
- Obsolete Intermediate Artifact

不得把無正當歷史治理價值的垃圾內容移入 `archive/` 代替清除。

完成條件：

`UNJUSTIFIED_RESIDUAL_FILES = 0`

<!-- SECTION_UID: WEB-GOV-01-S012 -->
## 12. 需求定義 Gate

正式設計前 MUST 建立：

- Project Scope
- Business Goal
- Target User
- Functional Requirements
- Non-functional Requirements
- Role Definition
- Out-of-Scope Definition
- Glossary
- Naming Registry Initial State

未完成 MUST 標示 `REQUIREMENT_INCOMPLETE`。

<!-- SECTION_UID: WEB-GOV-01-S013 -->
## 13. Architecture Gate

MUST 定義：

- System Architecture
- Module Map
- Dependency Map
- Navigation Architecture
- User Flow
- Business Flow
- State Machine
- Data Flow
- Frontend / Backend Boundary
- External Integration Boundary

Architecture 階段 MUST_NOT 直接建立未經定義的正式 Business Runtime。

<!-- SECTION_UID: WEB-GOV-01-S014 -->
## 14. Module Registry

每個 Module MUST 具備：

- Module UID
- Canonical Name
- Purpose
- Owner
- Parent
- Pages
- Runtime Scope
- Dependency
- Status

<!-- SECTION_UID: WEB-GOV-01-S015 -->
## 15. Page Registry

每個 Page MUST 具備：

- Page UID
- Canonical Name
- Display Name
- Route
- Module UID
- Purpose
- Parent UID
- Required Permission
- Design Owner
- Implementation Owner
- Visual Status
- Implementation Status

<!-- SECTION_UID: WEB-GOV-01-S016 -->
## 16. Design System Gate

大量頁面設計前 MUST 建立統一 Design System，至少包含：

- Color Tokens
- Typography Tokens
- Spacing Tokens
- Radius Tokens
- Border Tokens
- Shadow Tokens
- Icon Rules
- Button Variants
- Input Variants
- Card Variants
- Table Variants
- Modal Variants
- Drawer Variants
- Responsive Tokens

頁面 MUST 引用 Token，不得每頁自行創造視覺值。

<!-- SECTION_UID: WEB-GOV-01-S017 -->
## 17. Layout System

每個共用 Layout MUST 定義：

- Layout UID
- Viewport
- Header Region
- Navigation Region
- Main Content Region
- Auxiliary Panel Regions
- Footer Region
- Width / Height Rules
- Min / Max Rules
- Grid
- Gap
- Padding
- Overflow
- Collapse Rules
- Responsive Rules

<!-- SECTION_UID: WEB-GOV-01-S018 -->
## 18. Grid System

MUST 定義：

- Container Width
- Column Count
- Gutter
- Outer Margin
- Breakpoints
- Section Span Rules

MUST_NOT 依每次生成結果重新決定 Grid。

<!-- SECTION_UID: WEB-GOV-01-S019 -->
## 19. Component Registry

正式共用 Component MUST 具有：

- Component UID
- Canonical Name
- Owner File
- Purpose
- Variant List
- Dimension Rules
- Typography
- Tokens
- States
- Responsive Rules
- Allowed Usage
- Version

同義 Component MUST_NOT 重複建立。

<!-- SECTION_UID: WEB-GOV-01-S020 -->
## 20. Page Design 必填規格

每個 Page Design MUST 完整定義：

- Page UID
- Canonical Name
- Purpose
- Route
- Viewport
- Layout UID
- Grid
- Sections
- Components
- Controls
- Fields
- Assets
- Typography Tokens
- Color Tokens
- Spacing Tokens
- Dimensions
- Position
- Alignment
- States
- Responsive Behavior
- Localization Keys
- User Flow
- Visual Anchors
- Locked Regions
- Editable Regions
- Current Visual Reference

缺失關鍵欄位不得進 Visual Generation Gate。

<!-- SECTION_UID: WEB-GOV-01-S021 -->
## 21. Section 規格

重要 Section MUST 定義：

- Section UID
- Canonical Name
- Parent UID
- Purpose
- Grid Position
- Dimensions
- Padding
- Gap
- Background Token
- Border Token
- Overflow
- Responsive Behavior

<!-- SECTION_UID: WEB-GOV-01-S022 -->
## 22. Control 規格

Control MUST 定義：

- Control UID
- Canonical Name
- Type
- Label Key
- Icon Reference
- Position
- Dimensions
- Default State
- Hover State
- Focus State
- Active State
- Loading State
- Disabled State
- Success State
- Error State
- Visibility Condition
- Permission Reference
- Action Reference

<!-- SECTION_UID: WEB-GOV-01-S023 -->
## 23. Field 規格

Field MUST 定義：

- Field UID
- Canonical Name
- Type
- Label Key
- Placeholder Key
- Required
- Default Value
- Validation Rules
- Length / Range Rules
- Read-only Rule
- Disabled Rule
- Permission Reference
- Localization Key

<!-- SECTION_UID: WEB-GOV-01-S024 -->
## 24. Asset Registry

所有正式圖片、標誌、圖示、背景、插圖、縮圖、Avatar 或其他視覺素材 MUST 建立 Asset UID。

每個 Asset MUST 定義：

- Asset UID
- Canonical Name
- Asset Type
- File Reference
- Source Type
- Version
- Width
- Height
- Aspect Ratio
- Usage
- Allowed Crop
- Allowed Resize
- Allowed Modification
- Color Treatment
- Status

<!-- SECTION_UID: WEB-GOV-01-S025 -->
## 25. Asset Binding

視覺素材不得使用模糊描述作為正式綁定。

每個重要 Asset 使用位置 MUST 定義：

- Page UID
- Section UID
- Component UID
- Asset UID
- Position
- Width
- Height
- Aspect Ratio
- Crop Mode
- Focal Point
- Object Fit
- Object Position
- Opacity
- Overlay
- Lock Status

<!-- SECTION_UID: WEB-GOV-01-S026 -->
## 26. Asset Lock

Asset 狀態 MUST 使用：

- `DRAFT`
- `REVIEW`
- `APPROVED`
- `LOCKED`

`LOCKED` Asset MUST_NOT 被 AI 自行替換、重生、裁切、改色、改構圖或改變用途。

<!-- SECTION_UID: WEB-GOV-01-S027 -->
## 27. Visual Generation Manifest

每次正式視覺生成前 MUST 建立獨立 Generation Manifest，至少包含：

- Generation UID
- Page UID
- Design Version
- Reference Visual UID
- Design System Version
- Layout UID
- Component Versions
- Asset UIDs
- Viewport
- Language
- Theme
- Change Level
- Change Set UID
- Locked Areas
- Editable Areas

<!-- SECTION_UID: WEB-GOV-01-S028 -->
## 28. 強制 Visual Preview Gate

規劃與 Page Design 完成後 MUST_NOT 直接進入正式 Frontend Implementation。

必須先：

1. 依 Design Spec、Asset Binding 與 Generation Manifest 產生頁面視覺預覽。
2. 預覽 MUST 以實際網站畫面結構為目標，不得只產生概念圖或 Moodboard。
3. 進入 `VISUAL_REVIEW`。
4. 由授權確認者檢查。
5. 有問題則建立 Change Set。
6. 只修改 Change Set 指定區域。
7. 重新產生候選視覺。
8. 執行 Visual Drift Check。
9. 通過後標示 `VISUAL_APPROVED`。

未取得 `VISUAL_APPROVED` MUST_NOT 進入 Design Freeze。

<!-- SECTION_UID: WEB-GOV-01-S029 -->
## 29. 視覺修改分級

修改 MUST 先分類：

- `LEVEL_0_CONTENT`
- `LEVEL_1_MICRO`
- `LEVEL_2_COMPONENT`
- `LEVEL_3_SECTION`
- `LEVEL_4_PAGE_REDESIGN`
- `LEVEL_5_SYSTEM_REDESIGN`

LEVEL 0–3 MUST 預設保留所有未指定內容。

LEVEL 4–5 只有在正式變更要求明確允許時可使用。

<!-- SECTION_UID: WEB-GOV-01-S030 -->
## 30. Change Set

每次修改 MUST 建立獨立 Change Set，定義：

- Change UID
- Target UID
- Change Level
- Changed Properties
- Locked Properties
- Affected Dependencies
- Required Re-review

未列入 Change Set 的設計區域預設為 `LOCKED`。

<!-- SECTION_UID: WEB-GOV-01-S031 -->
## 31. Visual Anchor

每頁 MUST 定義固定 Visual Anchors，用於防止微調造成整體漂移。

Visual Anchor MUST 包含：

- Anchor UID
- Position Rule
- Dimension Rule
- Relationship Rule
- Lock Status

<!-- SECTION_UID: WEB-GOV-01-S032 -->
## 32. Canonical Visual

每個 Page 同一時間只能有一個 `CURRENT_CANONICAL_VISUAL`。

Candidate MUST 獨立保存且不得覆蓋 Approved Visual。

每個 Visual Candidate MUST 可追溯：

- Visual UID
- Parent Visual UID
- Generation UID
- Change UID
- Design Version
- Approval Status

<!-- SECTION_UID: WEB-GOV-01-S033 -->
## 33. Visual Drift Gate

未經 Change Set 產生下列變化 MUST 判定 `VISUAL_DRIFT_FAIL`：

- Layout Change
- Asset Change
- Typography Change
- Color Change
- Component Change
- Navigation Change
- Dimension Change
- Information Hierarchy Change

<!-- SECTION_UID: WEB-GOV-01-S034 -->
## 34. Audit Baseline 必須在施工前建立

Blueprint 階段 MUST 同時建立未來驗收標準。

每個可驗收治理單位 MUST 建立 Audit UID 與 Acceptance Matrix。

Audit Baseline MUST 定義：

- Audit UID
- Target UID
- Required Audit Items
- Required Tests
- Required Production Evidence
- Required Gates
- PASS Condition
- PARTIAL Condition
- FAIL Condition
- Definition of Done

不得等施工完成後才決定驗收方式。

<!-- SECTION_UID: WEB-GOV-01-S035 -->
## 35. Acceptance Requirement 狀態

每個驗收項目 MUST 預先標示：

- `REQUIRED`
- `OPTIONAL`
- `NOT_APPLICABLE`

施工階段 MUST_NOT 為了讓結果通過而將 `REQUIRED` 改為 `OPTIONAL` 或 `NOT_APPLICABLE`。

<!-- SECTION_UID: WEB-GOV-01-S036 -->
## 36. Design Freeze Gate

Design Freeze 前 MUST 全部通過：

- Requirement Gate
- Naming Gate
- Architecture Gate
- Navigation Gate
- User Flow Gate
- Page Registry Gate
- Design System Gate
- Layout Gate
- Component Gate
- Asset Registry Gate
- Asset Binding Gate
- Page Design Gate
- Visual Generation Gate
- Visual Review Gate
- Visual Approval Gate
- Audit Baseline Gate
- Acceptance Matrix Gate
- Definition of Done Gate

全部 PASS 後才可標示：

`DESIGN_FROZEN`

<!-- SECTION_UID: WEB-GOV-01-S037 -->
## 37. Design Freeze Package

每個正式施工單位在進入 Implementation 前 MUST 具備：

- Canonical UID
- Canonical Name
- Owner File
- Page / Capability Spec
- Layout Mapping
- Component Mapping
- Control / Field Mapping
- Asset Mapping
- Responsive Spec
- Current Canonical Visual
- Generation Manifest
- Audit Baseline
- Acceptance Matrix
- Definition of Done
- Design Version

<!-- SECTION_UID: WEB-GOV-01-S038 -->
## 38. Design Change Procedure

Design Freeze 後若要變更設計 MUST：

1. 建立正式 Change Request。
2. 確認 Target UID。
3. 建立 Change Set。
4. 解除必要 Lock。
5. 更新 Design Spec。
6. 更新 Asset Binding（如受影響）。
7. 重新產生 Visual Candidate。
8. 完成 Visual Review。
9. 更新 Canonical Visual。
10. 更新 Design Freeze Package。
11. 更新受影響 Audit Baseline。
12. 標記受影響施工項目為 `REVERIFY_REQUIRED`。

MUST_NOT 只改程式而不更新上游設計 Authority。

<!-- SECTION_UID: WEB-GOV-01-S039 -->
## 39. 藍圖完成輸出

第一階段完成後 MUST 產生：

- Authority Registries
- Architecture Files
- Naming Registry
- Page Registry
- Design System
- Layout Definitions
- Component Definitions
- Asset Registry
- Page Design Files
- Asset Binding Files
- Approved Visual References
- Generation Manifests
- Audit Baselines
- Acceptance Matrices
- Definitions of Done
- Design Freeze Packages

以上為第二份正式施工規範的唯一入口基準。

<!-- SECTION_UID: WEB-GOV-01-S040 -->
## 40. 禁止事項

MUST_NOT：

- 未搜尋就建新檔。
- 同義重複命名。
- 以不同名稱建立第二套功能。
- 用自然語言描述取代 UID。
- 用檔名版本尾碼代替正式版本控制。
- 將所有正式內容塞進單一巨型檔案。
- 將每個微小屬性過度拆成獨立檔。
- 規劃完成後跳過 Visual Preview。
- 視覺未批准即開始正式 Frontend。
- 微調時重新生成整頁設計。
- 未經 Change Set 修改 Locked Region。
- Candidate 覆蓋 Current Canonical Visual。
- Design Freeze 後由 Implementation 反向改寫產品設計。
- 在施工後才降低 Acceptance Requirement。



<!-- SECTION_UID: WEB-GOV-01-S040A -->
## 40A. 原始施工來源 Intake 與污染判真 Gate

任何 Page、Capability、Module 或跨頁 Flow 在建立 Blueprint 前，MUST 先執行 `SOURCE_INTAKE_GATE`，不得從中途 Design、Implementation 或既有畫面直接開始。

每一個輸入來源 MUST 建立 Source Record，至少包含：

- Source UID
- Source Path / External Reference
- Source Hash
- Source Type
- Claimed Authority Role
- Canonical UID / Scope（如可解析）
- Owner Claim
- Version / Revision
- Approval / Lock State
- Supersedes / Superseded By
- Current Authority Membership
- Production Usage（如適用）
- Conflict State
- Contamination State
- Resolution Result
- Evidence Reference

來源分類狀態 MUST 使用：

- `CURRENT_CANONICAL`
- `REFERENCE_ONLY`
- `HISTORICAL`
- `SUPERSEDED`
- `DUPLICATE`
- `FOREIGN_SCOPE`
- `GENERATED_NON_AUTHORITY`
- `CONFLICTING`
- `UNRESOLVED`

AI MUST_NOT 因檔名包含 `final`、`locked`、`current`、較新日期或較新 Commit 就直接判定為 Current Authority。

判真 MUST 綜合：

1. Current Authority Manifest / Registry。
2. Canonical UID 與 Canonical Owner。
3. 正式 Supersession / Deprecation 關係。
4. Design / Contract Approval 與 Lock State。
5. Source Revision 與可追溯 Evidence。
6. Production Runtime Evidence 僅可證明「目前實際跑什麼」，MUST_NOT 單獨反向改寫產品設計 Authority。
7. 若資料互相矛盾且無唯一裁決依據，MUST 標示 `AUTHORITY_CONFLICT` 並停止該 Scope 的 Effectful Implementation。

### Source Contamination Guard

下列任一狀態 MUST 視為污染候選並進入裁決：

- 已被 Supersede 的舊內容混入 Current 檔。
- 同一 UID 在不同檔案出現互斥定義。
- 同一 Canonical Name 對應不同 Owner。
- Generated / Evidence / Historical Snapshot 被當成 Product Authority。
- Production 現況快照被寫回 Design Authority。
- 舊 Navigation、Permission、Runtime、Database 或 Visual Contract 殘留於 Current Owner。
- 新舊 Payload 混合且無 Source-to-Target Mapping。

污染內容 MUST 被分類、隔離、移除或降級為 Reference；MUST_NOT 靜默合併成新的 Current Authority。

完成條件：

- `UNRESOLVED_SOURCE_TRUTH = 0`
- `CURRENT_OWNER_CONFLICT = 0`
- `CURRENT_SOURCE_CONTAMINATION = 0`
- `UNMAPPED_SUPERSEDED_CONTENT = 0`

<!-- SECTION_UID: WEB-GOV-01-S040B -->
## 40B. 統一頁面複雜度 Profile

所有頁面 MUST 使用同一套 Governance、Lifecycle 與 Audit Gate。頁面複雜度只用來判定某些 Step 是否適用，MUST_NOT 用來縮短治理流程或降低驗收標準。

Page Complexity Profile MUST 從下列類型選擇或組合：

- `P1_READ_ONLY`：讀取、列表、檢視為主。
- `P2_INTERACTIVE`：具有輸入、篩選、對話、Drawer/Modal、局部狀態。
- `P3_EFFECTFUL`：會建立、修改、刪除、批准、鎖定、發布或寫入資料。
- `P4_CROSS_PAGE`：輸出會成為其他頁面或 Module 的輸入。
- `P5_ASYNC_EXTERNAL`：涉及 Queue、Worker、Provider、Storage、Webhook 或外部平台。
- `P6_SECURITY_SENSITIVE`：具有細粒度 Permission、Sensitive Data、RLS 或高風險操作。

同一頁可同時符合多個 Profile。所有被判定 `NOT_APPLICABLE` 的 Gate MUST 有正式理由與 Evidence。

<!-- SECTION_UID: WEB-GOV-01-S040C -->
## 40C. Functional Chain Planning Baseline

Blueprint 階段 MUST 為每一個正式功能重建完整前後鏈，而不是只列出 Control 或 API。

標準功能鏈為：

`Business Intent -> Preconditions -> Entry -> Operator/System Input Source -> Control/Trigger -> Gate -> Permission -> Action -> Validation -> Payload -> API/Entry -> Runtime Owner -> Repository/Data/Provider -> Audit Event -> Response -> UI/Caller Feedback -> Success State -> Next State -> Next Step -> Next Gate -> Failure State -> Retry/Recovery/Rollback -> Terminal Outcome`

每一節點 MUST 標示：

- Required / Optional / Not Applicable
- Canonical UID
- Canonical Owner
- Input / Output Contract
- Previous Node
- Next Node
- Error Behavior
- Audit Item UID

### Gap Classification

功能鏈缺口 MUST 分類為：

- `AUTO_REMEDIABLE`：Authority 與前後 Contract 唯一決定缺失步驟，可安全自動補齊。
- `IMPLEMENTATION_GAP`：Authority 已明確要求，但 Implementation 缺一層或未綁定。
- `SHARED_OWNER_REFERENCE`：正式 Shared Owner 已存在，MUST Reference，禁止重複建立。
- `INPUT_SOURCE_GAP`：Runtime/Payload 需要輸入，但 UI、Derived Rule 或其他正式來源未定義。
- `AUTHORITY_GAP`：知道流程斷裂，但存在兩種以上合理產品行為；MUST BLOCK，禁止 AI 猜。
- `ARCHITECTURE_GAP`：Transport、Projection、Permission、State 或 Cross-page Contract 未定義。
- `INTENTIONAL_FAIL_CLOSED`：Authority 明確要求阻擋；MUST 保留，禁止為了 Gate 變綠而解除。
- `TEST_ONLY_BEHAVIOR`：Fixture/Mock/Controlled Test 行為，不得冒充 Production Contract。

### Auto-remediation Boundary

只有 `AUTO_REMEDIABLE` 與 Authority 唯一明確的 `IMPLEMENTATION_GAP` MAY 自動建立修補 Work Unit。

MUST_NOT 自動：

- 發明 Default Work Item。
- 發明 Input 值或 Decision。
- 將 TEST_ONLY 固定值帶入 Production。
- 新增與 Shared Owner 重複的 Runtime / API / Permission / Data Owner。
- 在多個合理產品行為中自行選一個。

<!-- SECTION_UID: WEB-GOV-01-S040D -->
## 40D. Cross-page Flow Contract

任何跨頁功能 MUST 建立 `FLOW UID` 並明確定義：

- Source Page / Capability
- Exit State
- Exported Identity / Data
- Transition Trigger
- Navigation / Routing Contract
- Target Page / Capability
- Target Entry State
- Required Permission
- Shared Runtime / Data Dependency
- Failure / Resume Behavior
- Back / Cancel Behavior
- Audit / Evidence

只驗單頁內部 PASS 不得取代 Cross-page Flow PASS。

<!-- SECTION_UID: WEB-GOV-01-S040E -->
## 40E. Visual Geometry Contract

每個 Page 的 Current Design MUST 除了視覺圖外，建立可機器驗證的 Geometry Baseline，至少包含：

- Viewport / Breakpoint UID
- Container Width / Min / Max
- Grid Columns / Span / Gutter / Outer Margin
- Section Bounding Rules
- Component / Control / Field Width / Height Rules
- Min / Max Width / Height
- Gap / Padding / Alignment
- Aspect Ratio
- Overflow / Scroll Rule
- Collapse / Stack / Wrap Rule
- Z-order / Overlay Rule（如適用）
- Text Capacity / Truncation / Wrap Rule
- Asset Object-fit / Object-position
- Locked Visual Anchors
- Allowed Tolerance / Diff Threshold

Geometry Baseline MUST 以 Design Token、Layout Rule 與正式尺寸規格為來源，MUST_NOT 由每次生成結果反推成新規格。

### Visual Geometry Failure

至少下列狀態 MUST 可被檢測：

- Element Overlap
- Unexpected Clipping
- Horizontal Overflow
- Unapproved Scroll
- Container Overflow
- Text Overflow / Ellipsis Drift
- Control Compression
- Input/Button Below Defined Minimum
- Aspect Ratio Drift
- Misalignment
- Unexpected Wrap / Stack
- Occlusion by Sticky/Fixed Layer
- Responsive Breakpoint Drift
- Navigation / Header / Main Content Collision

### Safe Visual Auto-fix

只有 `LEVEL_1_MICRO` 且可在既有 Token、Grid、Locked Anchor 與 Geometry Baseline 內唯一修正的問題 MAY 自動微調。

若修正會改變 Section 尺寸、資訊層級、Grid Span、主要元件比例、Navigation 或 Locked Region，MUST 建立正式 Change Set，重新走 Visual Review，不得以「自動微調」越權重設計。

<!-- SECTION_UID: WEB-GOV-01-S041 -->
## 41. 文件完成條件

本文件對應階段只有在所有必要 Blueprint Gate 與 Design Freeze Gate PASS 後才可標示：

`BLUEPRINT_READY_FOR_IMPLEMENTATION`


<!-- SECTION_UID: WEB-GOV-01-S058 -->
## 58. v2.1.0 Source Truth / Authority Provenance Gate

正式 Page / Module 在 Blueprint Intake 前 MUST 建立 `SOURCE_TRUTH_LEDGER`，且 Validator MUST 由來源紀錄自行重算 Current Owner，不得信任人工填寫的總計欄位。

每個來源 MUST 記錄：`source_uid`、`source_path`、`source_hash`、`canonical_uid`、`authority_role`、`authority_status`、`current_owner_uid`、`positive_ui_authority`、`derived_from`、`supersedes`、`superseded_by`、`evidence_ref`。

同一 `canonical_uid + authority_scope` 若存在兩個以上可寫入的 Current Positive Authority，MUST 判定 `AUTHORITY_CONFLICT`。

`DRAFT`、`REFERENCE_ONLY`、`HISTORICAL`、`SUPERSEDED`、`GENERATED_NON_AUTHORITY`、`EXECUTION_ARTIFACT` MUST_NOT 成為 Current Positive Authority。

Current Snapshot / Current Active Pointer MAY 指向 Canonical Owner，但 MUST_NOT 因內容完整而升格為第二 Authority。

舊檔即使自稱 `FINAL` 或 `CURRENT`，若較新的 Current Authority 已明確 supersede / replace / current-only，MUST 依正式 supersession lineage 降級，不得依檔名、日期或 Production 現況猜測。

<!-- SECTION_UID: WEB-GOV-01-S059 -->
## 59. v2.1.0 Action Effect / Functional Chain Semantics

Functional Chain MUST 先解析 Authority 的 `effect_type` / `runtime_binding`，再決定哪些節點需要 API / Runtime / Persistence。

`UI_ONLY`、`CONTEXT_STATE` 等 Authority 明確宣告 `api_required=false` 的 Action MAY 將 API/Runtime/Persistence 標記為 `NOT_APPLICABLE`，但 MUST 同時保存 Authority Evidence；不得用字串 `N/A` 欺騙 Effectful Chain。

`EXTERNAL_EFFECTS_REQUIRED`、`CONVERSATION_WRITE`、`JOB_START`、`DRAFT_MUTATION`、`VERSION_CREATE`、`VERSION_LOCK`、`DECISION_MUTATION`、`SCORE_MUTATION`、`HANDOFF_CREATE` 等 effectful Action MUST 有 Authority 指定的 Runtime/Port/API/Shared Owner 與 Effect Evidence；缺任一必要節點 MUST BLOCK。

Required Production Capability 若分類為 `INTENTIONAL_FAIL_CLOSED`、`TEST_ONLY_BEHAVIOR` 或 `production_eligible=false`，MUST_NOT 被 Functional Chain Gate 判為 PASS。

<!-- SECTION_UID: WEB-GOV-01-S060 -->
## 60. v2.1.0 Complex Page State Machine Gate

若 Page Authority 定義 State/Stage Transition Registry，Blueprint MUST 產出 Machine-readable `STATE_TRANSITION_LEDGER`。

每個 transition MUST 綁定：Transition UID、From State/Stage、To State/Stage、Trigger/Action、Gate/Preconditions、Mutation Owner、Failure State、Recovery、Audit/Event、Illegal Transition Tests。

Validator MUST 確認所有 Required Action 的 transition 唯一、不得跳 stage、不得從 UI 自行發明 next state。

<!-- SECTION_UID: WEB-GOV-01-S061 -->
## 61. v2.1.0 Async / Provider Lifecycle Gate

任何 `JOB_START` / Provider / Queue / Worker Action MUST 明確定義：request identity、input fingerprint、idempotency、queued/running/succeeded/failed/cancel/retry eligibility、callback/result provenance、output persistence、audit correlation。

UI 顯示 `completed` MUST 以 Runtime/Provider materialized result 為依據，MUST_NOT 以按鈕 click 或 optimistic state 冒充完成。

<!-- SECTION_UID: WEB-GOV-01-S062 -->
## 62. v2.1.0 Field Identity / Generated ID Gate

若 Page Authority 定義 Conceptual Object → Canonical Field → UI Label → Localization Key → Validation Contract，施工 MUST 保持該 lineage。

Database / Runtime 產生的 ID、Version、Checksum、Canonical Filename MUST 為 read-only projection；Frontend MUST_NOT 自行生成、猜測、解析檔名或覆寫。


## v2.1.0 Pilot Hardening — Shared Owner / Port Resolution

- Effectful functional-chain validation MUST distinguish page-local execution from `SHARED_OPERATION_REFERENCE`, `SOURCE_INTEGRATION_PORT`, `COMPOSITE_TO_EXISTING_EXECUTE_PORT`, and equivalent registered owner bindings.
- A shared owner reference MUST_NOT be treated as a missing page-local API/runtime. The validator MUST resolve the exact owner + operation/port reference before opening an implementation gap.
- AI MUST_NOT create a duplicate API, runtime, repository, database owner, or provider adapter merely because the page authority delegates execution to a shared owner.
- `NOT_APPLICABLE` for page-local transport/data nodes is legal only when exact shared-owner Authority evidence explains where that responsibility is owned.


## v2.1.0 Pilot Hardening — Multi-representation Authority / Machine Encoding Mirror

- The same conceptual Authority MAY exist as a human-readable design document and a machine-readable encoding only when exactly one canonical editable owner is declared.
- A machine encoding, generated mirror, snapshot, export, or compiled representation MUST declare `canonical_owner_ref`; machine mirrors MUST also provide current semantic synchronization evidence.
- A mirror MUST_NOT become a second positive editable Authority merely because it says `FINAL`, `LOCKED`, `CURRENT`, has a newer file timestamp, or contains more fields.
- Human document ↔ machine encoding drift MUST block construction until reconciled to the declared owner; filename suffixes, upload dates and embedded `derived_validation: PASS` are not proof of current truth.
- Embedded self-validation / derived-validation inside an Authority file is provenance only and MUST_NOT satisfy a current validation-run Gate.

<!-- SECTION_UID: WEB-GOV-01-S063 -->
## 63. Stage-1 Correction — Source Domain Extraction Separation

This correction is scoped only to the governance defect reproduced during Source Intake testing. It does not authorize website implementation.

Before any Page Blueprint or Visual Blueprint may be treated as current planning input, mixed Raw Source MUST be decomposed at the extraction boundary into independent planning-domain outputs.

For every required Page, Source Intake MUST produce exactly one current `PAGE_CONSTRUCTION_EXTRACTION` and exactly one current `VISUAL_CONSTRUCTION_EXTRACTION` before planning closure.

The two extraction outputs MUST use different artifact UIDs, different physical target paths, and different editable owner UIDs. A mixed Raw Source MAY remain as immutable `REFERENCE_ONLY_SOURCE_SNAPSHOT`, but MUST_NOT be promoted directly as either current planning owner.

Each extraction output MUST record source lineage down to source section/reference scope, source hash/revision, extraction artifact hash, target role, and canonical owner reference.

Facts shared by Page Construction and Visual Construction MUST be referenced through a single shared fact/authority UID. Shared facts MUST_NOT be copied into two independently editable owners.

`PAGE_CONSTRUCTION_DESIGN` MUST be derived only from approved Page Construction extraction outputs plus explicitly referenced shared facts. `VISUAL_CONSTRUCTION_DESIGN` MUST be derived only from approved Visual Construction extraction outputs plus explicitly referenced shared facts.

Missing domain extraction, same target path, same editable owner, missing section lineage, direct promotion of a mixed source, or duplicate shared-fact ownership MUST BLOCK Source Intake closure.

During governance-system development and validation, these rules govern test fixtures and extraction evidence only. They MUST_NOT be interpreted as authorization to begin formal product, site, application, or page reconstruction for any governed implementation.

<!-- SECTION_UID: WEB-GOV-01-S064 -->
## 64. Stage-1 Bugfix — Classified Responsibility Materialization and Base Blueprint Compilation

This bugfix is scoped only to the Stage-1 defect discovered after the v2.1.1 extraction-domain lock. It does not authorize formal website reconstruction and does not redefine product/page authority.

<!-- SECTION_UID: WEB-GOV-01-S064-01 -->
### 64.1 Two-level decomposition is mandatory

Source Intake MUST perform two independent decomposition levels before a Base Blueprint may close:

1. **Planning-domain split** — mixed Raw Source is separated into `PAGE_CONSTRUCTION` and `VISUAL_CONSTRUCTION` extraction domains.
2. **Governed-responsibility split** — each domain is further materialized into responsibility-scoped Canonical Classification Artifacts.

A domain-level extraction file that still contains multiple independently governed responsibilities MUST be treated as an intermediate extraction container, not as the final classified owner.

<!-- SECTION_UID: WEB-GOV-01-S064-02 -->
### 64.2 Responsibility-scoped classification contract

Every extracted source segment MUST be mapped to exactly one of:

- one Canonical Classification Artifact; or
- one `SHARED_FACT_REFERENCE` owned elsewhere; or
- one justified `REFERENCE_ONLY` / `NOT_APPLICABLE` disposition with Authority evidence.

Each classification artifact MUST declare at least:

- `artifact_uid`
- `page_uid`
- `planning_domain`
- `responsibility_uid`
- `responsibility_class`
- `canonical_owner_uid`
- `target_path`
- `lifecycle_uid`
- `approval_scope_uid`
- `version_scope_uid`
- `test_scope_uid`
- `source_lineage[]` with exact source segment refs
- `artifact_hash`
- `status`

`ONE GOVERNED RESPONSIBILITY = ONE CANONICAL OWNER` remains binding.

Multiple source segments MAY map to the same Canonical Classification Artifact when they share the same governed responsibility. Multiple independently governed responsibilities MUST_NOT be merged into one editable artifact merely for convenience.

`MIXED_ALLOWED` is legal only when the artifact records evidence that all contained responsibilities share the same Owner, Lifecycle, Approval, Version, and Test Scope. Missing proof means `SPLIT_REQUIRED`.

<!-- SECTION_UID: WEB-GOV-01-S064-03 -->
### 64.3 Source mapping closure

The extraction/classification ledger MUST allow the validator to recompute, from source-segment facts rather than self-reported summary fields:

- `UNCLASSIFIED_REQUIRED_CONTENT = 0`
- `UNMAPPED_REQUIRED_CONTENT = 0`
- `MULTI_MAPPED_REQUIRED_CONTENT = 0`
- `LOST_REQUIRED_CONTENT = 0`
- `DUPLICATE_CANONICAL_OWNER = 0`
- `UNRESOLVED_MIXED_RESPONSIBILITY = 0`
- `BROKEN_REFERENCE = 0`
- `PAGE_VISUAL_CROSS_CONTAMINATION = 0`

Self-declared PASS, COMPLETE, zero-count summaries, or precomputed blocker totals MUST_NOT satisfy this gate.

<!-- SECTION_UID: WEB-GOV-01-S064-04 -->
### 64.4 Base Blueprint compilation boundary

A Base Blueprint MUST be a composition/index artifact compiled from approved Canonical Classification Artifacts and Shared Fact References. It MUST_NOT become another copy of their payloads.

A Base Blueprint MUST declare:

- `blueprint_uid`
- `page_uid`
- `blueprint_type: BASE_BLUEPRINT`
- exact input artifact UIDs and hashes
- required responsibility coverage
- shared references
- unresolved gap references
- source-truth / authority refs
- compilation run UID
- compiler/governance version
- blueprint hash
- status

Base Blueprint compilation MUST satisfy:

- no direct Raw Source consumption after classification closure;
- no direct mixed-domain source consumption;
- every required responsibility input resolves to exactly one current Canonical Classification Artifact or justified Shared Fact Reference;
- no embedded full classification payload duplicate;
- no second editable owner for classified content;
- missing or stale input hash => `REVERIFY_REQUIRED`;
- any unresolved required classification/gap => `BLOCKED`.

<!-- SECTION_UID: WEB-GOV-01-S064-05 -->
### 64.5 Clean workspace / zero garbage

Every Stage-1 retry MUST start from an empty current test-output workspace. Previous-run extracted/classified/blueprint outputs MUST be removed from the Current Test Workspace before the new run starts. Historical evidence MAY be retained only in the dedicated evidence ledger/archive location and MUST_NOT be loadable as current input.

After each Stage-1 mutating batch, the validator MUST detect and block unreferenced artifacts, abandoned split files, temporary copies, backups, generated caches, duplicate payload copies, and stale previous-run outputs.

A successful retry therefore proves both correct classification and **zero unexplained residual artifacts**.

<!-- SECTION_UID: WEB-GOV-01-S065 -->
## 65. Stage-1 Bugfix — Source Enumeration Completeness and Blueprint Domain Separation

This correction closes two defects reproduced by the first clean Source-to-Blueprint retry. It remains Stage-1 governance work only.

<!-- SECTION_UID: WEB-GOV-01-S065-01 -->
### 65.1 Independent source-structure enumeration

Before source segments may be classified, every Raw Source MUST have one immutable `SOURCE_STRUCTURE_MANIFEST` entry captured from the observed source structure.

For each Raw Source, the structure entry MUST include:

- `source_uid`
- immutable source identity/hash/revision or external source snapshot reference
- enumeration method/tool evidence
- capture run UID/timestamp/evidence ref
- every observed structural node/section that can contain governed content
- each node's stable `source_node_uid` and source location/ref
- governance relevance: `REQUIRED`, `REFERENCE_ONLY`, or `NON_NORMATIVE`

The Source Segment Map MUST reference `source_node_uid`; it MUST_NOT invent a parallel free-text section list that cannot be reconciled to the structure manifest.

Every `REQUIRED` source node MUST have exactly one legal segment/disposition. A run MUST FAIL when a required source node is absent from the segment map, duplicated into multiple segments without an explicit split contract, or silently omitted from classification.

A validator MUST recompute coverage from the Source Structure Manifest and MUST_NOT trust a self-reported `all_sections_mapped`, `coverage=100%`, or zero-count summary.

If the source bytes/complete machine parse are unavailable, the run MUST be marked `SOURCE_ENUMERATION_NOT_PROVEN` and MUST_NOT claim full-source extraction closure. A partial governance-mechanics pilot may continue only when explicitly labeled partial and non-production-complete.

<!-- SECTION_UID: WEB-GOV-01-S065-02 -->
### 65.2 Page and Visual Base Blueprints remain independent

For every Page, Stage-1 MUST materialize exactly two independent Base Blueprints:

- `PAGE_BASE_BLUEPRINT` — consumes only current `PAGE_CONSTRUCTION` classification artifacts and permitted Shared Fact References.
- `VISUAL_BASE_BLUEPRINT` — consumes only current `VISUAL_CONSTRUCTION` classification artifacts and permitted Shared Fact References.

They MUST have different Blueprint UIDs, different physical target paths, different editable owners, independent hashes, and independent required-responsibility coverage.

A combined editable Base Blueprint that owns both Page and Visual payloads is FORBIDDEN.

A non-owning `BLUEPRINT_BINDING_MANIFEST` MAY be required to bind the two blueprints by UID/hash for downstream coordination. The binding manifest MUST_NOT duplicate either blueprint payload and MUST_NOT become a third editable planning authority.

A Page Base Blueprint MUST_NOT consume Visual classification artifacts. A Visual Base Blueprint MUST_NOT consume Page classification artifacts. Any cross-domain dependency is expressed only by UID/reference.

<!-- SECTION_UID: WEB-GOV-01-S065-03 -->
### 65.3 Retry closure

A Stage-1 retry may close only when all of the following are independently proven:

- source structure enumeration complete for the claimed scope;
- all required source nodes legally disposed;
- responsibility-scoped classification complete;
- Page/Visual classified ownership remains separate;
- one Page Base Blueprint and one Visual Base Blueprint exist per Page;
- binding hashes are current;
- no direct Raw Source input after classification closure;
- no unexplained current-output residuals;
- no stale prior-run output reused;
- normative candidate hash unchanged for the active run.



<!-- SECTION_UID: WEB-GOV-01-S066 -->
## 66. Program Source Naming / Construction Artifact Registration

Program source files are governed construction artifacts. Their names and paths MUST be resolved before code generation begins.

Every program artifact MUST be registered with at least: Program Artifact UID, Work Unit UID, Page/Scope UID, Construction Profile, Canonical Name, Canonical Path, Canonical Filename, Owner UID, Producer Stage UID, Input Artifact Refs, Required Normative Refs, Dependency Refs, Reverse Dependency Refs, Acceptance Audit Blueprint Ref, Required Test Refs, Current Hash, and Status.

A framework-reserved filename such as `page.tsx`, `layout.tsx`, `route.ts`, `loading.tsx`, `error.tsx`, or `not-found.tsx` is permitted only as a controlled filename exception. The filename itself MUST_NOT become identity; the registered Canonical Path + Program Artifact UID + Owner UID remain authoritative.

Program filenames MUST_NOT be invented during implementation. `new`, `final`, `latest`, `fixed`, `backup`, `copy`, `temp`, and equivalent unmanaged suffixes are forbidden for Current construction artifacts.

<!-- SECTION_UID: WEB-GOV-01-S067 -->
## 67. Index-First Construction Loading

All construction stages MUST resolve artifacts through the registered index before opening source content. The default read path is:

`ROOT / STAGE MANIFEST -> ARTIFACT INDEX -> EXACT ARTIFACT -> DEPENDENCY CLOSURE -> REQUIRED NORMATIVE REFS`

Whole-package rescans are forbidden for ordinary Work Unit execution. They are allowed only for explicit integrity, migration, or audit operations whose scope requires a full scan.

Splitting files without an index is insufficient. Every split artifact MUST retain UID, Owner, Hash, Parent/Scope, forward dependency and reverse dependency continuity.
<!-- SECTION_UID: WEB-GOV-01-S068 -->
## 68. Canonical Section UID / Exact Normative Reference Governance

Every normative H2/H3 clause MUST have a stable `SECTION_UID` registered in `10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml`.

Construction indexes, Work Units, Implementation Manifests, validators, acceptance blueprints, and audit items MUST reference normative clauses by `SECTION_UID`; free-text display headings MUST_NOT be used as canonical reference identity.

Within one normative document every canonical numeric section number MUST be unique. A duplicate numeric group is a blocking numbering defect and MUST be normalized before freeze. Renumbering MUST preserve a migration record from legacy number/title to the new canonical number and `SECTION_UID`.

A normative reference is valid only when the Section Registry resolves the UID to exactly one current document path and the physical document contains the matching `SECTION_UID` anchor. Zero matches or multiple matches MUST block execution.

<!-- SECTION_UID: WEB-GOV-01-S069 -->
## 69. Stage-1 Source Context / Supersession / Dependency Contracts

Before Base Blueprint compilation, Stage 1 MUST materialize three independent source-fact artifacts for every required page/scope:

- `SOURCE_CONTEXT_MANIFEST`
- `CONTENT_SUPERSESSION_CONFLICT_LEDGER`
- `SOURCE_DEPENDENCY_MAP`

`SOURCE_CONTEXT_MANIFEST` MUST preserve source parent/child, previous/next, cross-file reference, page/module scope, source node identity, and lineage relationships required to understand the original construction context.

`CONTENT_SUPERSESSION_CONFLICT_LEDGER` MUST identify old/current/conflicting/duplicate content, authority disposition, superseded-by relation, conflict decision evidence, and downstream reverify impact. Superseded content MUST_NOT remain a Current owner.

`SOURCE_DEPENDENCY_MAP` MUST contain only dependencies explicitly supported by source/authority evidence. Unknown functional dependency MUST be recorded as `UNRESOLVED_AUTHORITY_GAP`; AI MUST_NOT invent a dependency merely to close the graph.

An Authority reference that is explicitly present in captured Raw Source but whose Authority file/runtime contract is outside the current capture scope is **not** a Source Fact failure and MUST_NOT be reclassified as an invented dependency. It MUST remain a machine-readable `UNRESOLVED_AUTHORITY_GAP` with stable `gap_uid`, exact `authority_ref`, captured consumer source UID(s), and physical evidence reference. Source Fact closure is legal while such gaps remain unresolved only when every gap is explicitly preserved.

No AI, compiler, validator, Blueprint generator, construction runtime, QA step, or Release Gate may silently drop, ignore, auto-fill, infer, alias-substitute, default, or mark such a gap satisfied. Resolution requires materialized authoritative source, exact Authority-reference match, Authority content hash, and Authority evidence reference. Until that proof exists, the unresolved identity MUST be carried forward unchanged through Responsibility Classification, Base Blueprint, Blueprint Binding, Compiler, Runtime Construction, Validation/QA, and Release Gate. Any count or identity drift is blocking.

Each Page/Visual Base Blueprint MUST reference the current hashes of these source-fact artifacts. It MUST_NOT duplicate their editable payload. If the page/scope is affected by unresolved external Authority gaps, the Blueprint MUST also carry them explicitly in `unresolved_external_authority_refs` with the same `gap_uid`, `authority_ref`, and `UNRESOLVED_AUTHORITY_GAP` disposition; it MUST_NOT represent them as satisfied. Affected Blueprint/execution closure that requires the missing Authority is fail-closed until authoritative resolution evidence is present.

<!-- SECTION_UID: WEB-GOV-01-S070 -->
## 70. Canonical Management Artifact Materialization

Naming, Blueprint, Audit Catalog, Review Progress, Lifecycle Stage Contract, Acceptance Audit Blueprint, Section Registry, Protected Current Artifact Registry, Root Manifest, and Construction Artifact Index are Current governance machine artifacts and MUST physically exist in the package before formal governance test begins.

A prose-only declaration of any such registry/contract MUST_NOT satisfy materialization. Every Current management artifact MUST have one canonical path, one owner UID, one current hash, and one schema/version identity.

<!-- SECTION_UID: WEB-GOV-01-S071 -->
## 71. Product-Neutral Applicability / Business Entity Lifecycle & Hierarchy Completeness

This governance specification is product-neutral and system-neutral. It MUST be usable by any governed website, web application, AI-assisted application, information system, workflow platform, or comparable software product. A product name, repository name, page UID, route, provider, database schema, department name, or product-specific runtime MUST_NOT be a prerequisite for interpreting the common rules.

Product-specific material MAY appear only as empirical provenance, synthetic test fixtures, migration compatibility aliases, or explicitly registered Product Profile extensions. Such material MUST_NOT narrow the common denominator, override a common invariant, or become Current common Authority. A Product Profile MAY add stricter requirements or domain-specific entities; it MUST_NOT weaken or replace the product-neutral common rules.

Before a Page, Surface, Module, Workflow, or comparable interaction scope may close functional design, it MUST materialize a `BUSINESS_ENTITY_INVENTORY`, a `BUSINESS_ENTITY_OPERATION_MATRIX`, and an `ENTITY_HIERARCHY_MATRIX` for every business entity exposed, created, selected, modified, confirmed, versioned, categorized, ordered, locked, approved, archived, or otherwise managed by that scope.

A user-manageable child such as an item, category, chapter, section, entry, task, version, asset, record, configuration, rule, package, or equivalent concept MUST be treated as a Business Entity when it has its own identity, state, ordering, parent binding, editable content, lifecycle, or user-visible operation. Merely rendering a list or selector does not satisfy entity completeness.

Every Business Entity MUST declare an applicability decision for at least: `DISCOVER_OR_LIST`, `SELECT_OR_OPEN`, `CREATE`, `CREATION_MODE`, `PARENT_BIND`, `CATEGORY_OR_GROUP_BIND`, `DRAFT`, `RESUME`, `EDIT`, `SAVE`, `VALIDATE`, `CONFIRM_OR_APPROVE`, `VERSION`, `REVISE`, `LOCK_OR_UNLOCK`, `REORDER`, `MOVE_OR_REPARENT`, `ARCHIVE_OR_DELETE`, `RESTORE`, `DEPENDENCY_IMPACT`, `AUDIT`, `ERROR_RECOVERY`, and `NEXT_STEP`. Each operation MUST be `REQUIRED`, `OPTIONAL`, or `NOT_APPLICABLE`. `NOT_APPLICABLE` MUST carry explicit Authority evidence; blank, omitted, inferred, or silently ignored operations are forbidden.

Every `REQUIRED` operation MUST resolve a complete functional contract including business intent/user journey, trigger/control or system event, input source, payload schema, validation, permission/gate, Authority reference, prerequisite state, resulting state/transition, runtime owner, persistence or state owner when applicable, audit event, failure/error binding, recovery/rollback disposition, user/system feedback, and next action/terminal disposition.

Every parent/child or category/group relationship MUST define exact parent identity, child identity, cardinality, creation entry, payload/reference binding, ordering semantics when applicable, permission, state dependency, version dependency, move/reparent rule, archive/delete propagation, upstream-change impact, downstream revalidation, and Authority evidence. An entity that is listed or selectable but has no governed creation/modification/finalization path is incomplete.

Functional completeness MUST be measured by `Business Entity × Applicable REQUIRED Operation`, not by counts of Pages, Controls, Actions, APIs, Ports, Components, or rendered elements. A scope with all declared Controls/Actions present MAY still fail if a required entity lifecycle operation or hierarchy edge is absent.

Functional completion MUST be bounded. Before any AI, compiler, planner, or construction agent proposes a missing upstream/downstream function, it MUST materialize a `FUNCTION_ADMISSION_SCORECARD` and an `AUTO_COMPLETION_SCOPE_LEDGER`. A proposed addition MUST identify the exact seed gap or REQUIRED operation, Current Authority or deterministic required dependency, existing-capability reuse check, alternative-path check, and the user-task/system-terminal outcome that is blocked without the function.

The scorecard MAY calculate a 0-100 necessity/utility score for prioritization, but score is diagnostic and MUST_NOT create Authority. `AUTHORITY_NECESSITY`, `TASK_COMPLETION_CRITICALITY`, `DEPENDENCY_BLOCKING_IMPACT`, `ERROR_RISK_REDUCTION`, `USER_REACH_OR_FREQUENCY`, `REUSE_ACROSS_REQUIRED_FLOWS`, and `ACCESSIBILITY_OR_RECOVERY_IMPACT` MUST be evidence-backed. A high utility score without Current Authority or a uniquely required dependency MUST remain Review-only; it MUST_NOT authorize auto-expansion.

Automatic completion is permitted only for the minimal closure set needed to close the registered REQUIRED gap. Generic CRUD completion, sibling-feature symmetry, "best practice" expansion, speculative convenience features, or adding a new Business Entity merely because a related Entity exists are forbidden. Every transitive dependency MUST independently pass admission. Auto-completion MUST traverse only the frozen registered dependency closure; discovery of a new dependency or Entity outside that closure MUST stop automation and reopen functional/visual design. Cycles MUST be detected and blocked. Completion MUST stop immediately when the seed REQUIRED gaps are closed and no unresolved REQUIRED edge remains inside the frozen closure.

Every admitted function MUST also classify visual impact through a `FUNCTION_VISUAL_IMPACT_MATRIX`. A user-visible or user-observable function MUST define the visual section/surface, component/control identity, interaction entry, state binding, pending/loading state, permission/disabled state, success/error/recovery feedback, version/revision visibility when applicable, responsive/overflow behavior, i18n reference when applicable, accessibility semantics, and visual Authority. `NO_VISUAL_DELTA` is allowed only with explicit Authority evidence. A new visual pattern MUST_NOT be invented during implementation when an approved existing design-system pattern is available.


<!-- SECTION_UID: WEB-GOV-01-S072 -->
## 72. Functional Workbench Cohesion / Interaction Topology / AI-Assisted Continuity

This section governs not only whether a function exists, but whether a contiguous functional journey is assembled as one coherent interaction unit. Every continuous user or system work sequence MUST be classified as one of `ATOMIC_WORKBENCH`, `SAME_SURFACE_CLUSTER`, `CROSS_SURFACE_FLOW`, or `INDEPENDENT_SUPPORT_PANEL`, and MUST materialize a `FUNCTIONAL_WORKBENCH_CONTRACT` plus an `INTERACTION_TOPOLOGY_MATRIX` before visual layout is approved.

The `FUNCTIONAL_WORKBENCH_CONTRACT` MUST identify the functional cluster UID, business journey, required operations, shared context identity, workbench class, visual-container requirement, required operation order, adjacency requirements, same-surface requirement, allowed separation modes, forbidden interruptions, cross-surface transition contract, context-handoff contract, responsive-reflow rule, and Authority reference. An atomic workbench MUST_NOT be fragmented by an unrelated panel, dashboard, approval block, analytics block, or support surface between operations that require immediate continuity. Mere presence of all controls/components does not prove workbench cohesion.

The `INTERACTION_TOPOLOGY_MATRIX` MUST preserve the authoritative topology from functional design into visual design: operation sequence, grouping, adjacency, interruption boundary, surface-transition boundary, shared context/state identity, and continuation/recovery path. Stage-03 MAY change geometry and responsive placement only within the allowed topology. An unapproved visual reorder, separation, or insertion that breaks the required operation chain is a functional defect, not a cosmetic preference.

When a scope declares `AI_CONVERSATION`, `AI_ASSISTED_WORKSPACE`, or `MULTI_AGENT_INTERACTION`, the common AI-assisted interaction profile becomes conditionally mandatory. It MUST materialize an `AI_INTERACTION_CONTINUITY_MATRIX` without making AI a requirement for non-AI products. The profile MUST preserve conversation/context identity across declared mode changes, distinguish preserve/fork/replace/terminate transitions, prevent silent context reset, prevent raw generative output from silently becoming authoritative state, preserve revision lineage back to exact base evidence/version, and isolate branches until an explicit governed adoption step occurs.

Conversation identity continuity MUST classify at least `conversation_id`, `thread_id`, `context_ref_or_hash`, `work_scope_ref`, and `base_version_ref_when_applicable`. Multi-agent comparison MUST prove input equivalence using the same original-request identity and exact relevant-context snapshot unless registered Authority explicitly permits participant-specific context. Different inputs MUST_NOT be presented as a directly comparable same-baseline result.

AI output formalization MUST distinguish `RAW_AI_OUTPUT`, `WORKING_EVIDENCE`, `CANDIDATE`, `GOVERNED_DECISION`, and `AUTHORITATIVE_VERSION` or semantically equivalent product-neutral states. Direct promotion from raw AI output to authoritative state without the registered decision/approval boundary is forbidden. A returned revision MUST retain exact base candidate/version, reason/evidence, and source conversation/evidence continuity. A branch MUST bind to its exact source message/reference, own branch thread/context snapshot, isolation rule, and explicit adoption path; silent merge into the mainline is forbidden.

<!-- SECTION_UID: WEB-GOV-01-S073 -->
## 73. Canonical Stage Preflight / Effective Contract Overlay / Role-Safe Functional Closure

Every governed Stage MUST establish one canonical execution preflight before the first product/contract remediation begins. The preflight MUST resolve the governing rule universe once, freeze that universe for the attempt, and materialize the following machine-readable artifacts from Current Authority and the immutable predecessor baseline:

- `REQUIRED_FIELD_MANIFEST`
- `FUNCTIONAL_CHAIN_MANIFEST`
- `EFFECTIVE_CONTRACT_OVERLAY`
- `DEPENDENCY_TOPOLOGY`
- `DENOMINATOR_SNAPSHOT`
- `CLASSIFICATION_RULESET`
- `CHANGE_IMPACT_MAP`
- `STAGE_EXECUTION_PREFLIGHT_RECEIPT`

`REQUIRED_FIELD_MANIFEST` is the only canonical required-field universe for scanners, trace builders, validators, remediation classifiers and checkpoint reconciliation. A local runner MUST_NOT hard-code, omit, narrow, or independently reinterpret a subset while claiming canonical completeness. Applicability MUST be classified before a missing node is counted: every governed requirement is `REQUIRED`, `OPTIONAL`, or `NOT_APPLICABLE`, and `NOT_APPLICABLE` requires exact governing evidence.

Current Effective Contract truth is computed as `Immutable Raw/Predecessor Requirement + Legally Admitted Current Successor/Materialization Overlay`. Raw absence alone MUST_NOT be counted as an effective gap when an exact, validated, role-correct successor closure already satisfies the same canonical signature. Conversely, a neighboring value, same-UID membership, semantic similarity, or earlier test result MUST_NOT substitute for the missing role.

For every existing authorized function, incomplete before/after flow remains a functional defect and MUST be evaluated against the complete chain: `Business Intent -> Preconditions -> Entry -> Input Source -> Trigger -> Gate -> Permission -> Action -> Validation -> Payload -> API/Runtime -> Persistence/Provider -> Audit -> Response/Feedback -> Success/Next -> Failure/Recovery -> Terminal`. Absence of a pre-materialized exact value is not by itself an `AUTHORITY_GAP`. The executor MUST first run `UNIQUE_FUNCTIONAL_CLOSURE_DERIVATION` over the frozen dependency closure.

A missing step is `AUTO_REMEDIABLE` only when exactly one role-correct minimal closure is determined by Current Authority plus upstream/downstream contracts and no materially distinct product behavior remains. Two or more materially distinct viable behaviors MUST be recorded and classified `AUTHORITY_GAP`; zero role-correct derivations remain an owning-layer unresolved contract gap unless another registered class applies. Discovery of a required dependency outside the frozen closure MUST stop automation and reopen design.

Role identity is non-substitutable. In particular: port exposure is not a trigger; a state/event signal is not a trigger without an explicit binding; an action/runtime owner is not a transition mutation owner; result/state-event evidence is not itself a validation contract; a dotted event token is not an Audit Event UID without exact registered identity; and a neighboring same-UID field is not proof of the missing field. A minimal assertion wrapper MAY be generated from one unique frozen success signal only when its assertion semantics and observation point are uniquely determined and no alternative result/timing interpretation remains.
