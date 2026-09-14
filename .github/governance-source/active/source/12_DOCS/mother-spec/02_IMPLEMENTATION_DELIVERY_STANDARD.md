---
document_id: WEB-GOV-02
version: 2.1.0
order: 2
category: implementation_delivery
required_before_execution: true
requires: WEB-GOV-01
status: normative
permanent_inheritance: true
---

# 02 藍圖封板後正式施工、測試、部署與驗收規範

<!-- SECTION_UID: WEB-GOV-02-S000 -->
## 0. 規範目的

本文件定義在 `DESIGN_FROZEN` 後，如何依既有 Authority、Contract、Audit Baseline 與 Acceptance Matrix 將系統完整實作至可正式使用。

本階段 MUST_NOT 重新規劃、重新命名、重新設計或自行降低驗收標準。

<!-- SECTION_UID: WEB-GOV-02-S001 -->
## 1. 正式施工入口 Gate

開始任何正式施工前 MUST 確認：

- Project Scope 已封板。
- Naming Registry 已封板。
- Architecture 已建立。
- Page / Capability Registry 已建立。
- Design System 已建立。
- Approved Visual 已存在。
- Asset Binding 已完成。
- Audit Baseline 已建立。
- Acceptance Matrix 已建立。
- Definition of Done 已建立。
- Design Freeze Package 已完整。

任一 REQUIRED 項缺失時 MUST 標示：

`BLUEPRINT_INCOMPLETE`

並停止該 Work Unit 的 Implementation。

<!-- SECTION_UID: WEB-GOV-02-S002 -->
## 2. 施工 Authority

正式施工 MUST 同時依據：

- Blueprint
- Naming Authority
- Design Freeze Package
- Current Canonical Visual
- Contract Requirement
- Audit Baseline
- Acceptance Matrix
- Definition of Done

Implementation MUST_NOT 自行取代上述 Authority。

<!-- SECTION_UID: WEB-GOV-02-S002A -->
## 2A. 後續更新施工入口

本文件不只適用於第一次正式施工，也永久適用於後續新增、修改、修復、重構與版本更新。

每次 Change Request 進入 Implementation 前 MUST：

1. 取得 Current Revision。
2. 解析 Change Impact Set。
3. 找到所有受影響 Canonical Owners。
4. 確認是否涉及 Design Freeze。
5. 確認是否涉及 Contract、Runtime、Database、Permission、Integration、Test 或 Production Gate。
6. 先搜尋既有實作，不得直接新增平行檔案。
7. 對受影響 Audit Items 標示 `REVERIFY_REQUIRED`。
8. 按相同 Acceptance Matrix 與 Definition of Done 重新閉環。

若變更只修改既有 Governed Unit，MUST 更新既有 Owner。

若變更建立真正新的 Governed Unit，才可依第一份規範建立新的 Canonical UID 與 Owner。

MUST_NOT 使用版本副檔、同義新名稱或第二 Runtime 來迴避既有 Owner。

<!-- SECTION_UID: WEB-GOV-02-S003 -->
## 3. Audit Baseline 保護

施工階段 MUST_NOT：

- 刪除 REQUIRED Audit Item。
- 將 REQUIRED 改為 OPTIONAL。
- 將未完成項目改成 NOT_APPLICABLE。
- 以較低測試層級取代原 Required Test。
- 以非正式環境證據取代正式環境 Required Evidence。

驗收標準如需調整，MUST 走 Authority Change Procedure。

<!-- SECTION_UID: WEB-GOV-02-S004 -->
## 4. 正式施工總順序

每個 Work Unit MUST 依序執行：

1. Blueprint Intake
2. Blueprint Validation
3. Audit Baseline Intake
4. Acceptance Matrix Validation
5. Dependency Mapping
6. Duplicate / Conflict Pre-check
7. Contract Materialization
8. Repository Owner Resolution
9. Shared Foundation Verification
10. Frontend Implementation
11. Control / Field Implementation
12. Action Layer
13. Backend Runtime
14. Repository / Data Access Layer
15. Database Schema / Migration
16. Authentication
17. Authorization
18. Data Security
19. Audit / Logging
20. Error Contract
21. External Integration
22. Async Runtime
23. Storage Runtime
24. Unit Test
25. Integration Test
26. Database Test
27. Permission Test
28. Browser E2E
29. Control Acceptance
30. Visual Regression
31. Responsive Verification
32. Localization Verification
33. Accessibility Verification
34. Security Verification
35. Audit Matrix Reconciliation
36. Production Build
37. Staging Deployment
38. Staging Acceptance
39. Production Configuration
40. Production Migration
41. Production Deployment
42. Production Smoke
43. Production Browser Acceptance
44. Production Page Acceptance
45. Production Control Acceptance
46. Production Database Acceptance
47. Production Effectful Acceptance
48. External Integration Acceptance
49. Async Runtime Acceptance
50. Monitoring Verification
51. Backup Verification
52. Rollback Verification
53. Final Audit Matrix Reconciliation
54. Final Production Acceptance

MUST_NOT 任意跨越 REQUIRED Step。

<!-- SECTION_UID: WEB-GOV-02-S005 -->
## 5. Blueprint Intake

開始 Work Unit 前 MUST 解析：

- Work Unit UID
- Canonical Name
- Owner File
- Module UID
- Parent UID
- Design Version
- Current Canonical Visual
- Required Components
- Required Controls / Fields
- Required Actions
- Required Assets
- Required Permissions
- Runtime Mapping
- Database Mapping
- Audit UID
- Required Gates
- Required Tests
- Required Evidence

<!-- SECTION_UID: WEB-GOV-02-S006 -->
## 6. Blueprint Validation

MUST 驗證：

- UID 唯一。
- Canonical Name 一致。
- Owner 唯一。
- Reference 可解析。
- Design 為 Frozen。
- Visual 已 Approved。
- Route / Entry 定義完整。
- Permission 定義完整。
- User Flow 完整。
- Audit Baseline 可解析。

任何關鍵衝突 MUST 先治理再施工。

<!-- SECTION_UID: WEB-GOV-02-S007 -->
## 7. Acceptance Matrix Validation

施工前 MUST 確認所有 Audit Item 已標示：

- Requirement Type
- Acceptance Condition
- Evidence Requirement
- Gate
- Current Status

禁止空白 REQUIRED Item。

<!-- SECTION_UID: WEB-GOV-02-S008 -->
## 8. Dependency Mapping

每個 Work Unit MUST 建立直接依賴圖，至少涵蓋：

- Shared Runtime
- Shared Component
- Data Dependency
- Permission Dependency
- External Integration Dependency
- Async Dependency
- Configuration Dependency
- Test Dependency

必要 Dependency 未達可用狀態時，該 Work Unit 不得宣稱 Closed。

<!-- SECTION_UID: WEB-GOV-02-S009 -->
## 9. Contract Materialization

Effectful Capability MUST 建立可追溯鏈：

`Control -> Action -> Validation -> Permission -> API/Entry -> Runtime -> Repository -> Database/Provider -> Audit Event -> Response -> UI Feedback`

每個節點 MUST：

- 有 UID。
- 有 Owner。
- 有 Contract。
- 有錯誤行為。
- 有對應 Audit Item。

<!-- SECTION_UID: WEB-GOV-02-S010 -->
## 10. Repository 與檔案治理

Implementation MUST 使用既定正式目錄與 Owner File。

MUST_NOT：

- 建立同義第二資料夾。
- 以 `new`、`final`、`fix`、`copy` 等名稱建立平行正式版本。
- 因修改方便另開第二 Runtime。
- 將不同 Domain 的大量 Business Logic 塞進同一巨型檔案。
- 修改 Generated Artifact 當作正式 Source。

<!-- SECTION_UID: WEB-GOV-02-S010A -->
## 10A. Classification / Owner Integrity Gate

任何 Implementation 前後都 MUST 維持：

- Canonical Owner 唯一。
- Cross-class Reference 可解析。
- Required Content 無遺失。
- Critical Duplicate = 0。
- Critical Mixed Owner = 0 或具有正式 `MIXED_ALLOWED` 理由。
- Semantic Terminal Unit MUST 與單一治理責任同質；語法/檔案/物件/模組邊界不得直接當作責任邊界。
- `MIXED_TERMINAL_UNITS = 0` 且 `UNRESOLVED_CONTAINER_UNITS = 0` 才可關閉 Implementation/Delivery Gate；若混合責任跨 Owner、Lifecycle、Approval、Version、Test/Acceptance、Release/Rollback/Applicability Identity，MUST 先遞迴拆分或提出完整 `MIXED_ALLOWED` 證據。
- Second-System Conflict = 0。
- Broken Reference = 0。
- Unjustified Residual File = 0。

若施工造成檔案搬移、拆分、合併或 Owner 變更，MUST 同步更新：

- Naming Registry
- Owner Registry
- Source-to-Target Mapping
- Contract References
- Imports
- Tests
- Audit Matrix
- Evidence References

不得完成新 Owner 後仍保留舊完整 Payload 作為可解析正式來源。

<!-- SECTION_UID: WEB-GOV-02-S011 -->
## 11. Frontend Production Grade

Frontend 必須忠實於 Design Freeze，並至少處理：

- Layout Fidelity
- Component Fidelity
- Asset Fidelity
- Default State
- Loading State
- Empty State
- Populated State
- Disabled State
- Permission State
- Error State
- Success State
- Responsive Behavior
- Localization
- Accessibility Basics

Frontend MUST_NOT 自行新增、移動、刪除或重新分類產品功能。

<!-- SECTION_UID: WEB-GOV-02-S012 -->
## 12. Control Production Grade

每個重要 Control MUST 驗證：

- Rendered
- Visibility Rule
- Enabled Rule
- Disabled Rule
- Action Binding
- Permission Binding
- Loading Behavior
- Success Feedback
- Failure Feedback
- Audit Event

只有外觀沒有 Action 的 Control 不得 PASS。

<!-- SECTION_UID: WEB-GOV-02-S013 -->
## 13. Field Production Grade

Field MUST 同時落實：

- Client Validation（如適用）
- Server Validation
- Required Rule
- Type Rule
- Range / Length Rule
- Read-only Rule
- Disabled Rule
- Permission Rule
- Error Feedback
- Persistence Behavior

<!-- SECTION_UID: WEB-GOV-02-S014 -->
## 14. Backend Runtime Production Grade

Runtime SHOULD 依需求處理：

- Input Validation
- Authentication Context
- Authorization
- Business Rules
- State Transition
- Idempotency
- Concurrency
- Transaction
- Error Handling
- Retry / Timeout
- Audit
- Output Contract

只有 `request -> data write -> response` 而沒有必要治理邏輯的 Runtime 不得視為完成。

<!-- SECTION_UID: WEB-GOV-02-S015 -->
## 15. Data Access Layer

Database Access MUST 經正式 Repository / Data Access Owner。

MUST_NOT 將資料存取邏輯散落於：

- View Layer
- UI Event Handler
- Arbitrary Utility
- 未治理的 Script

<!-- SECTION_UID: WEB-GOV-02-S016 -->
## 16. Database Production Grade

依資料模型需求 MUST 建立與驗證：

- Schema
- Tables / Collections
- Columns / Fields
- Primary Identity
- Relationships
- Indexes
- Unique Rules
- Constraints
- State Fields
- Data Security Rules
- Migration
- Compatibility
- Test

Implementation MUST_NOT 自行創造未經 Authority 定義的新核心 Business Entity。

<!-- SECTION_UID: WEB-GOV-02-S017 -->
## 17. Migration Governance

所有結構性資料變更 MUST 透過不可變更的 Migration Unit。

Migration MUST 具備：

- Migration UID
- Canonical Name
- Sequence
- Source Revision
- Checksum
- Forward Procedure
- Compatibility Notes
- Rollback / Recovery Strategy
- Test Result
- Production Applied State

已套用 Migration MUST_NOT 被覆寫。

<!-- SECTION_UID: WEB-GOV-02-S018 -->
## 18. Authentication

如系統需要身份識別，MUST 驗證：

- Sign-in / Entry Authentication
- Sign-out / Session End
- Session Creation
- Session Refresh（如適用）
- Session Expiry
- Invalid Session
- Identity Binding
- Unauthorized Behavior

<!-- SECTION_UID: WEB-GOV-02-S019 -->
## 19. Authorization

Authorization MUST 在可信任執行層 Enforcement。

UI Visibility 不得替代 Backend Authorization。

敏感資料 SHOULD 另有 Data Layer Enforcement。

<!-- SECTION_UID: WEB-GOV-02-S020 -->
## 20. Data Security

依系統需要 MUST 定義與驗證：

- Tenant Isolation
- Owner Restriction
- Role / Policy Restriction
- Service Access Policy
- Row / Object Level Policy
- Sensitive Field Protection

<!-- SECTION_UID: WEB-GOV-02-S021 -->
## 21. Audit Runtime

重要 Effectful Operation MUST 記錄足以追溯的 Audit Data：

- Actor
- Action
- Resource
- Timestamp
- Request / Correlation ID
- Result
- Before / After（如適用）

<!-- SECTION_UID: WEB-GOV-02-S022 -->
## 22. Error Contract

正式 Error MUST 使用統一 Contract，至少包含：

- Error Code
- Technical Message
- User-safe Message
- Status / Category
- Retryable Flag
- Correlation Context
- Audit Context

MUST_NOT 只以 Console Output 作為正式錯誤處理。

<!-- SECTION_UID: WEB-GOV-02-S023 -->
## 23. External Integration Production Grade

外部系統 MUST 經正式 Adapter / Interface 層。

至少驗證：

- Configuration
- Credential Binding
- Request Mapping
- Response Validation
- Timeout
- Retry Policy
- Failure Mapping
- Audit
- Health / Availability Strategy

Business Runtime SHOULD 依賴抽象 Interface，而不是直接耦合單一供應商格式。

<!-- SECTION_UID: WEB-GOV-02-S024 -->
## 24. Secret Management

所有 Secret MUST：

- 不寫死於 Source。
- 不寫入公開 Log。
- 依 Environment 隔離。
- 只由授權 Runtime 讀取。
- 有 Rotation / Replacement Strategy（如適用）。

<!-- SECTION_UID: WEB-GOV-02-S025 -->
## 25. Async Runtime Production Grade

長時間或非同步工作如適用 MUST 管理：

- QUEUED
- RUNNING
- SUCCEEDED
- FAILED
- RETRYING
- CANCELLED

並驗證：

- Enqueue
- Worker / Consumer Binding
- Execution
- Retry
- Failure State
- Dead-letter Handling（如適用）
- Result Persistence
- UI / Caller State Update

<!-- SECTION_UID: WEB-GOV-02-S026 -->
## 26. Storage Production Grade

檔案與物件儲存如適用 MUST 處理：

- Upload
- Validation
- Storage
- Reference
- Version
- Permission
- Read / Download Policy
- Deletion
- Cleanup
- Retention

<!-- SECTION_UID: WEB-GOV-02-S027 -->
## 27. Test Layers

正式測試 MUST 依需要涵蓋：

- Unit
- Integration
- API / Entry
- Database
- Permission
- Browser
- End-to-End
- Production Acceptance

不得用大量低層測試數量掩蓋缺少必要 End-to-End 或 Production Verification。

<!-- SECTION_UID: WEB-GOV-02-S028 -->
## 28. Test Evidence

每次 Test MUST 綁定：

- Test UID
- Scope UID
- Source Revision ID
- Environment
- Result
- Timestamp
- Evidence Reference

舊 Revision 的 PASS 不得直接套用於新 Revision。

<!-- SECTION_UID: WEB-GOV-02-S029 -->
## 29. Browser End-to-End

核心 Flow MUST 在真實 Browser / Client 路徑驗證：

`Entry -> User Action -> Validation -> Runtime -> Persistence/Provider -> Response -> UI State`

只驗 HTTP/Transport 成功不得替代完整 E2E。

<!-- SECTION_UID: WEB-GOV-02-S030 -->
## 30. Page / Control Acceptance

每個正式 Page MUST 確認所有重要：

- Controls
- Fields
- Links
- Tabs
- Dialogs
- Drawers
- Navigation Entries

都具有正確：

- Visibility
- Permission
- Action
- Feedback
- Error Handling

<!-- SECTION_UID: WEB-GOV-02-S031 -->
## 31. Visual Regression

Implementation 完成後 MUST 與 Current Canonical Visual 及 Design Spec 比對：

- Layout
- Position
- Dimensions
- Spacing
- Typography
- Components
- Assets
- Responsive Behavior

未經 Change Set 的顯著差異 MUST FAIL。

<!-- SECTION_UID: WEB-GOV-02-S032 -->
## 32. Localization Verification

如系統支援多語系 MUST 驗證：

- Language Switching
- Missing Key
- Raw Key Leakage
- Text Overflow
- Layout Stability
- Canonical Identity 不受語言影響

<!-- SECTION_UID: WEB-GOV-02-S033 -->
## 33. Accessibility Verification

依適用範圍 SHOULD 驗證：

- Keyboard Navigation
- Focus State
- Labels
- Semantic Structure
- Contrast
- Dialog Focus Management
- Accessible Names

<!-- SECTION_UID: WEB-GOV-02-S034 -->
## 34. Security Verification

依風險與架構 MUST 驗證：

- Authentication Bypass
- Authorization Bypass
- Data Policy Bypass
- Injection
- Script Injection
- Request Forgery
- Secret Exposure
- Unsafe Upload
- Abuse / Rate Control
- Temporary Bypass

<!-- SECTION_UID: WEB-GOV-02-S035 -->
## 35. Audit Matrix 即時回填

每完成一個施工或測試項目 MUST 立即更新原 Acceptance Matrix。

每個 Audit Item 狀態只能使用：

- `NOT_STARTED`
- `IN_PROGRESS`
- `IMPLEMENTED`
- `REVERIFY_REQUIRED`
- `PASS`
- `PARTIAL`
- `FAIL`
- `BLOCKED`
- `NOT_APPLICABLE`
- `NOT_VERIFIED`

每個 `PASS` MUST 有 Evidence Reference。

<!-- SECTION_UID: WEB-GOV-02-S036 -->
## 36. 受影響 PASS 必須重開

後續修改只要影響已 PASS 的 Dependency，相關 Audit Item MUST 改為：

`REVERIFY_REQUIRED`

重新測試後才可恢復 PASS。

<!-- SECTION_UID: WEB-GOV-02-S037 -->
## 37. Production Build Gate

正式 Release 前 MUST 依專案技術棧完成必要：

- Static Validation
- Type / Schema Validation
- Compile / Build
- Production Startup
- Route / Entry Validation
- Runtime Bundle Validation

Development Runtime 成功不得取代 Production Build。

<!-- SECTION_UID: WEB-GOV-02-S038 -->
## 38. Staging Gate

如專案定義 Staging，Production 前 MUST 在 Staging 完成：

- Authentication
- Navigation
- Pages
- Controls
- Runtime
- Database
- Permission
- Async Runtime
- External Integration
- E2E
- Visual Regression

未 PASS 不得進 Production。

<!-- SECTION_UID: WEB-GOV-02-S039 -->
## 39. Production Configuration Gate

Production 前 MUST 驗證：

- Environment Configuration
- Production Data Target
- Secrets
- Domain / Entry Point
- External Integration Configuration
- Storage
- Callback / Webhook Configuration
- Monitoring
- Backup
- Rollback Readiness

不得使用 Development Configuration 冒充 Production Configuration。

<!-- SECTION_UID: WEB-GOV-02-S040 -->
## 40. Production Migration Gate

Production Migration MUST 記錄：

- Migration IDs
- Applied Count
- Checksum
- Target Environment
- Result
- Verification Result

Migration Source 存在不等於 Production Applied。

<!-- SECTION_UID: WEB-GOV-02-S041 -->
## 41. Production Deployment Gate

Deployment MUST 可追溯：

- Source Revision ID
- Release ID
- Build ID
- Deployment ID
- Environment
- Timestamp
- Status

Expected Source Revision MUST 與 Actual Deployed Revision 一致。

<!-- SECTION_UID: WEB-GOV-02-S042 -->
## 42. Production Smoke

正式部署後 MUST 立即驗證核心：

- Entry Point
- Health
- Readiness
- Authentication
- Session
- Navigation
- Critical Runtime
- Data Connectivity
- Exit / Sign-out（如適用）

<!-- SECTION_UID: WEB-GOV-02-S043 -->
## 43. Production Browser Acceptance

正式功能驗收 MUST 使用 Production Entry Point。

Local、Development、Preview 或 Staging PASS 不得取代 Production Browser Acceptance。

<!-- SECTION_UID: WEB-GOV-02-S044 -->
## 44. Production Page Acceptance

逐頁驗證：

- Route / Entry
- Render
- Navigation
- Visibility
- Controls
- Permission
- Assets
- Localization
- Responsive
- Layout Fidelity

<!-- SECTION_UID: WEB-GOV-02-S045 -->
## 45. Production Effectful Acceptance

所有 Release Scope 內的重要 Effectful Capability MUST 在 Production 或正式允許的等價驗收環境執行真實驗證。

驗證 MUST 涵蓋：

- Operation Trigger
- Authorization
- Runtime Execution
- Persistence / External Effect
- Audit
- Response
- UI / Caller State

MUST_NOT 以 Hardcoded Success、Fake Response 或 Mock Data 冒充正式驗收。

<!-- SECTION_UID: WEB-GOV-02-S046 -->
## 46. External Integration Acceptance

REQUIRED 外部整合必須確認：

- Credential Bound
- Adapter Bound
- Real Request
- Valid Response
- Failure Handling
- Audit

若外部必要條件未提供，狀態 MUST 為：

`BLOCKED_EXTERNAL_CONFIG`

不得 PASS。

<!-- SECTION_UID: WEB-GOV-02-S047 -->
## 47. Monitoring

Production SHOULD 至少監控：

- Application Error
- Runtime Error
- Data Error
- Async Failure
- External Integration Failure
- Latency
- Deployment Failure

<!-- SECTION_UID: WEB-GOV-02-S048 -->
## 48. Backup

如系統涉及持久化資料，Production MUST 定義與驗證：

- Backup Coverage
- Retention
- Last Successful Backup
- Restore Procedure
- Recovery Responsibility

<!-- SECTION_UID: WEB-GOV-02-S049 -->
## 49. Rollback

每次 Release MUST 有：

- Previous Stable Release Reference
- Rollback Procedure
- Data Compatibility Assessment
- Rollback Trigger
- Rollback Verification Method

<!-- SECTION_UID: WEB-GOV-02-S050 -->
## 50. Work Unit Closure

Work Unit 只有在下列全部成立後才能 `CLOSED`：

- 所有 REQUIRED Implementation 已完成。
- 所有 REQUIRED Audit Item 已 PASS。
- Required Evidence 已綁定。
- Direct Gap = 0。
- Critical Stub = 0。
- Critical Duplicate = 0。
- Critical Conflict = 0。
- Critical Orphan = 0。
- Required Regression 已 PASS。
- Definition of Done 全部滿足。

MUST_NOT 先 Closed 再補 Evidence。

<!-- SECTION_UID: WEB-GOV-02-S051 -->
## 51. Module Closure

Module Closure 前 MUST 驗證：

- 所有 Required Work Units Closed。
- 所有 Page / Capability 可追溯。
- Cross-unit Dependencies 無斷鏈。
- Shared Runtime 可用。
- Cross-page / Cross-capability Flow PASS。
- Module-level Audit PASS。

<!-- SECTION_UID: WEB-GOV-02-S052 -->
## 52. Release Candidate Gate

建立 Release Candidate 前 MUST：

- Scope Freeze。
- Required Work Units Closed。
- Audit Matrix Reconciled。
- Duplicate / Conflict / Orphan / Stub Guards PASS。
- Build PASS。
- Required Tests PASS。
- Migration Compatibility PASS。
- Security Gate PASS。

Release Candidate 後只允許處理 Release Blocker，MUST_NOT 任意加入新功能。

<!-- SECTION_UID: WEB-GOV-02-S053 -->
## 53. Final Production Acceptance

只有在下列 REQUIRED Gate 全部 PASS 後才可標示：

`PRODUCTION_READY`

至少包括：

- Release Revision Match
- Production Deployment
- Production Smoke
- Production Browser Acceptance
- Production Page Acceptance
- Production Control Acceptance
- Production Data Acceptance
- Required External Integration Acceptance
- Monitoring
- Backup
- Rollback
- Final Audit Matrix Reconciliation

<!-- SECTION_UID: WEB-GOV-02-S054 -->
## 54. 最終禁止事項

MUST_NOT：

- 施工階段重新設計已 Frozen UI。
- 施工階段重新命名 Canonical Identity。
- 建立第二套 Runtime、API、Database Truth 或 Permission System。
- 以 Placeholder、TODO、No-op、Fake Runtime、Fake Provider、Temporary Allow-all 冒充完成。
- 只完成 UI 就進下一個核心 Work Unit。
- 只完成 Runtime 不補必要 UI / Permission / Test。
- 只建立 Migration File 就宣稱 Production Migration 完成。
- 只 Deployment Success 就宣稱 Production Ready。
- 使用舊 Revision Evidence 冒充 Current Revision。
- 修改 Required Audit Item 以提高完成率。



<!-- SECTION_UID: WEB-GOV-02-S054A -->
## 54A. Page Full-Lifecycle Execution Gate

任何被選為 Pilot、正式施工或重新施工的 Page MUST 從 `SOURCE_INTAKE_GATE` 開始，不得從既有 UI、某個 Runtime、某個 Test 或某個中段 Commit 直接開始並宣稱完成全流程驗證。

固定生命周期為：

1. Raw Source Intake
2. Source Truth / Contamination Resolution
3. Canonical Classification
4. Source-to-Target Mapping
5. Naming / UID / Owner Resolution
6. Requirement Gate
7. Architecture / Dependency Gate
8. Page / Capability Registry
9. Functional Chain Planning
10. Cross-page Flow Mapping（如適用）
11. Design System Binding
12. Layout / Geometry Baseline
13. Component / Control / Field Spec
14. Asset Registry / Binding
15. Visual Generation Manifest
16. Visual Preview
17. Visual Review / Approval
18. Audit Baseline / Acceptance Matrix / DoD
19. Design Freeze
20. Repository Owner Resolution
21. Contract Materialization
22. Frontend / Control / Field Implementation
23. Action / Validation / Permission
24. API / Runtime / Repository / Data / Provider
25. State / Error / Audit / Recovery
26. Unit / Integration / DB / Permission Tests
27. Browser Functional E2E
28. Functional Chain Reconciliation
29. Visual Geometry Audit
30. Visual Regression
31. Responsive / Localization / Accessibility
32. Cross-page Flow E2E（如適用）
33. Security Verification
34. Production Build
35. Staging / Equivalent Acceptance（如適用）
36. Production Configuration / Migration
37. Production Deployment
38. Deployment Identity Verification
39. Production Smoke
40. Production Browser / Page / Control Acceptance
41. Production Functional Chain Acceptance
42. Production Visual Geometry / Responsive Acceptance
43. Production Data / Effectful / External / Async Acceptance（如適用）
44. Production Render Freshness Verification
45. Monitoring / Backup / Rollback
46. Final Audit Reconciliation
47. Closure

任一 REQUIRED Step 未 PASS，後續 Step MAY 被執行以蒐集證據，但該 Page MUST_NOT 標示 End-to-End Closed。

<!-- SECTION_UID: WEB-GOV-02-S054B -->
## 54B. Functional Chain Reconstruction 與補齊

正式施工前及施工後 MUST 重新計算每個功能鏈。

若缺口分類為：

- `AUTO_REMEDIABLE`：建立最小修補 Work Unit，PATCH 既有 Canonical Owner，測試後回鏈重算。
- `IMPLEMENTATION_GAP`：依既有 Authority 補 Implementation，不得新增第二套 Owner。
- `SHARED_OWNER_REFERENCE`：綁定既有 Shared Owner 並補 Reference/Test，禁止 Duplicate Runtime。
- `INPUT_SOURCE_GAP` / `AUTHORITY_GAP` / `ARCHITECTURE_GAP`：MUST BLOCK 對應 Production Closure，先補正式 Contract/Authority。
- `INTENTIONAL_FAIL_CLOSED`：保持 BLOCK，直到正式 Unlock Condition 成立。

自動補齊 MUST 以「補完整前後步驟」為目的，不得只為了讓 UI 看起來完整而新增按鈕。

<!-- SECTION_UID: WEB-GOV-02-S054C -->
## 54C. Visual Geometry Implementation Verification

Browser E2E 與 Production Browser Acceptance MUST 取得實際 Rendering Geometry，並逐 Breakpoint 驗證：

- Bounding Box
- Computed Width / Height
- Position / Alignment
- Scroll Width / Scroll Height
- Overflow State
- Visible / Hidden State
- Wrap / Stack State
- Text Clipping
- Overlay / Occlusion
- Grid / Flex Relationship

至少 MUST 驗證 Desktop、Tablet、Mobile 中所有 Design Baseline 指定的 Required Viewports。

若存在擠壓、錯位、比例漂移或未授權 Overflow：

1. 判斷是否 `LEVEL_1_MICRO`。
2. 若可唯一由 Token / Geometry Rule 修正，PATCH Existing Owner。
3. 重新執行 Visual Geometry + Visual Regression + Responsive Regression。
4. 若不是 Micro Fix，建立 Change Set 並回到 Visual Review。

MUST_NOT 只靠 Screenshot 目視判定「看起來差不多」。

<!-- SECTION_UID: WEB-GOV-02-S054D -->
## 54D. Deployment Build Identity Gate

Production Build MUST 產生可機器驗證的 `BUILD_IDENTITY_MANIFEST`，至少綁定：

- Source Revision
- Source Tree Hash
- Build ID
- Release ID（如已有）
- Route Manifest Hash
- Client Asset Manifest Hash
- Server Bundle / Entry Manifest Hash
- Design Version / Page Spec Hash（適用頁面）
- Generated At

Production Deployment MUST 提供可查詢的 Runtime Release Identity。實作方式 MAY 為受控 Endpoint、Response Header、HTML Meta 或等價機制，但 MUST 可由 Post-deploy Audit 自動讀取。

<!-- SECTION_UID: WEB-GOV-02-S054E -->
## 54E. Production Stale Render Guard

Deployment Success 不等於正式網址已更新。

Post-deploy MUST 同時驗證：

1. Expected Source Revision == Built Revision。
2. Built Revision == Deployed Revision。
3. Deployed Revision == Production Runtime Reported Revision。
4. Production Route Manifest 與本次 Build 相符。
5. Production 載入的 Client Assets 屬於本次 Build Manifest。
6. Production DOM Structure / Governed Control Fingerprint 與本次 Candidate 相符。
7. Production Visual Geometry 與 Current Canonical Visual / Geometry Baseline 相符。
8. Required Pages 不得仍呈現上一 Release 的已知 Fingerprint。

任一不一致 MUST 標示：

- `PRODUCTION_REVISION_MISMATCH`
- `PRODUCTION_ASSET_STALE`
- `PRODUCTION_DOM_STALE`
- `PRODUCTION_VISUAL_STALE`
- `PRODUCTION_CACHE_STALE`

並使 Production Acceptance FAIL。

不得以「部署平台顯示 Success」取代正式網址 Render Freshness Verification。

<!-- SECTION_UID: WEB-GOV-02-S054F -->
## 54F. Cross-page / System Logic Slice Test

全站系統邏輯 MUST 支援以 `FLOW UID` 為切片單位測試，而不是只能以 Page 為單位。

Slice MUST 可沿：

`Source Page -> Exit State -> Shared Runtime/Data -> Transition -> Target Page -> Target Entry State -> Next Action`

對每一 Slice 至少驗：

- Identity / Context 傳遞
- Permission Continuity
- State Transition
- Data Consistency
- Navigation / Routing
- Error / Retry / Resume
- Audit Continuity
- Production Evidence

跨頁 Slice FAIL MUST 使相關 Work Units 進 `REVERIFY_REQUIRED`。

<!-- SECTION_UID: WEB-GOV-02-S055 -->
## 55. 文件完成條件

本文件對應階段只有在 Final Production Acceptance PASS 後才可標示：

`IMPLEMENTATION_AND_DELIVERY_COMPLETE`


<!-- SECTION_UID: WEB-GOV-02-S059 -->
## 59. v2.1.0 Validation Run Identity / Freshness

每次正式 Validation MUST 建立唯一 `run_uid`，所有本次 Gate Evidence MUST 綁同一 `run_uid` 與 `source_revision`。

先前 Revision 或先前 Run 的 PASS MUST_NOT 直接替代 Current Run PASS。受影響 Source/Contract/Code/Visual/Config 變動後，相關 Gate MUST 轉為 `REVERIFY_REQUIRED`。

Timeout、Crash、未寫入 Terminal Result、Evidence Run UID 不一致 MUST fail-closed。

<!-- SECTION_UID: WEB-GOV-02-S060 -->
## 60. v2.1.0 Execution Cycle

每次執行 MUST 宣告 `execution_cycle`：`INITIAL_RELEASE`、`CHANGE_RELEASE`、`HOTFIX` 或 `MAINTENANCE`。

`INITIAL_RELEASE` MUST 實際消耗 Pre-release → Staging（若 Authority 定義）→ Production Deploy → Post-deploy Acceptance → Final Acceptance，不得以 Build PASS 冒充正式上線。

Change/Hotfix/Maintenance MUST 依 impact scope 重開受影響 Gate，且 MUST_NOT 重用失效 Evidence。

<!-- SECTION_UID: WEB-GOV-02-S061 -->
## 61. v2.1.0 Design Approval Timing

Visual Review MAY 在 Design Approval 前執行；正式 `DESIGN_APPROVAL` MUST 位於 Visual Review 完成後、Design Freeze boundary，並綁定同一 Design Revision / Canonical Visual。

Implementation MUST_NOT 使用尚未獲得正式 Design Approval 的 Freeze Package。

<!-- SECTION_UID: WEB-GOV-02-S062 -->
## 62. v2.1.0 Repository Boundary / Install Safety

Governance Installer 與 Generated Evidence MUST 限制在 declared repository root / governed paths 內。任何 `../` escape、絕對路徑寫出 repository boundary、或將測試輸出污染產品 source tree MUST FAIL。

<!-- SECTION_UID: WEB-GOV-02-S063 -->
## 63. v2.1.0 Deployment Applicability Coherence

當 Release Scope `deployment_applicable=true` 時，Release Gate MUST 實際消耗 Build、Deployment、Production Revision、Production Browser/DOM/Asset/Geometry Evidence；不得只有文件上標記 deployment required 而 executable gate 未引用。

當 `deployment_applicable=false` 時，MUST 有 Authority/Execution-Cycle Evidence 說明為何不適用，不得自行略過 Production。

<!-- SECTION_UID: WEB-GOV-02-S064 -->
## 64. v2.1.0 Production Route Render Freshness

正式網址驗收 MUST 同時核對：Expected Source Revision = Build Source Revision = Deployed Revision = Runtime Reported Revision，並核對 Route Manifest、Client Asset Manifest、Governed DOM Fingerprint、Visual Geometry、Capture Timestamp、Current `run_uid`。

Deployment Success 而 Production route 仍載入舊 DOM / 舊 Asset / 舊 Geometry MUST FAIL，分類為 `PRODUCTION_ASSET_STALE` / `PRODUCTION_DOM_STALE` / `PRODUCTION_VISUAL_STALE` / `PRODUCTION_CACHE_STALE`。

<!-- SECTION_UID: WEB-GOV-02-S065 -->
## 65. Stage-Gated Governance Validation Before Website Reconstruction

The governance package itself MUST be validated and locked before formal website reconstruction begins.

Governance validation proceeds one lifecycle step at a time. For step `N`:

1. define and freeze the candidate rules for step `N`;
2. bind the test run to the frozen candidate hash;
3. execute minimal-control / black-box tests for step `N`;
4. if a governance defect is reproduced, close that run as FAIL and record the defect before any rule edit;
5. open a bounded bugfix window for that defect only;
6. create a new candidate hash and rerun all tests required for step `N`;
7. once PASS is accepted, lock step `N` and prohibit further edits to that released rule set;
8. only then may step `N+1` validation begin.

A test run MUST_NOT modify normative governance files while the run is active. Editing the rule set to make an active test pass invalidates the run.

After a step is locked, later source extraction or later-stage testing MAY discover a new governance defect, but the locked release MUST remain immutable. The defect MUST be recorded and fixed in a subsequent governance candidate/version. All artifacts affected by that change MUST become `REVERIFY_REQUIRED` and be brought into conformance with the new released governance version.

Formal website implementation, page reconstruction, runtime construction, deployment, or Production Acceptance MUST remain blocked until the governance release is explicitly `FINAL_LOCKED_FOR_WEBSITE_RECONSTRUCTION`.



<!-- SECTION_UID: WEB-GOV-02-S057 -->
## 57. Program Construction Profile / Implementation Manifest

Before any program source file is written, the Work Unit MUST materialize an `IMPLEMENTATION_MANIFEST` that binds every program artifact to one registered Construction Profile.

Required profiles include at least: `UI_COMPONENT`, `CONTROL_HANDLER`, `API_ENTRY`, `RUNTIME_SERVICE`, `REPOSITORY_DATA_ACCESS`, `DATABASE_MIGRATION`, `ASYNC_WORKER`, `EXTERNAL_ADAPTER`, and `TEST_IMPLEMENTATION`.

The profile standardizes responsibility, required contracts, dependency declarations, error/audit behavior, and test obligations. It MUST_NOT force unrelated business logic into a universal code template.

The Implementation Manifest MUST be the primary construction navigation entry and MUST bind: governance revision, design freeze ref, naming registry ref, program artifacts, exact required normative refs, input artifact refs, dependency closure ref, acceptance audit blueprint ref, and required tests.

Code generation MUST consume the manifest first. The implementation MAY load only the declared references and dependency closure unless an explicit audit operation requires a wider scan.

<!-- SECTION_UID: WEB-GOV-02-S058 -->
## 58. Program Artifact Filename / Path Gate

A source file MUST NOT be created until its Program Artifact UID, canonical path, canonical filename, owner and Construction Profile are registered.

If a framework requires a reserved filename, the reserved filename is allowed only at the pre-registered path. Moving the file, creating a sibling copy, or introducing an alternative path requires a governed change and reference migration.

Implementation closure requires: canonical path match, owner match, profile compliance, import/reference closure, required test presence, and zero unmanaged duplicate source file.

<!-- SECTION_UID: WEB-GOV-02-S066 -->
## 66. Cross-Layer / Cross-Page Continuity Gate

Every required dependency edge MUST have both forward and reverse index entries. Required edge classes include Cross Layer, Cross Stage, Cross Page, Page/Visual Reference, Shared Owner Port, Provider/Async, and Data/Runtime.

A producer hash change MUST mark all dependent consumers `REVERIFY_REQUIRED` until their contracts/tests are revalidated. A cross-page handoff without a registered handoff/contract reference is BLOCKED.

No later implementation layer may repair an unresolved earlier-layer authority or dependency gap by inventing a second local behavior.
<!-- SECTION_UID: WEB-GOV-02-S067 -->
## 67. Full 11-Stage Machine Contract

The lifecycle MUST be machine-materialized as exactly eleven ordered stages: Source/Base Blueprint, Page Functional Contract, Visual Design, Foundation Freeze, Implementation, Verification/QA, Build/Release Candidate, Staging, Production Cutover, Production Acceptance, and Closure/Operations.

Every Stage Contract MUST define: stage UID, scope mode, entry gate, required inputs, input origins, operations, outputs, output producers, validators, required evidence, failure behavior, invalidation behavior, exit gate, and next-stage condition.

Stages 1–4 MUST use `ALL_REQUIRED_PAGES` foundation barriers. No required page may advance to Stage N+1 while another required page is incomplete at Stage N. Stages 5–11 MUST preserve one selected `page_uid` through Production Page Closure before the next page can begin implementation.

Delivery Steps 1–54 MUST each bind to exactly one real operation in the Lifecycle Stage Registry. Number-only stage ranges without operation bindings MUST_NOT satisfy the contract.

<!-- SECTION_UID: WEB-GOV-02-S068 -->
## 68. Mode-Aware Governance Validation

Governance validation MUST select one explicit validation mode:

- `PRE_FORMAL_DEFINITION_AUDIT`
- `STAGE_EXECUTION_VALIDATION`
- `RELEASE_FINAL_VALIDATION`

Pre-formal validation MUST validate governance definitions, registries, references, schemas, compilers, package self-containment, and hygiene only. It MUST_NOT require website execution or Production evidence that cannot yet legally exist.

Stage execution validation MUST validate the selected stage, applicable persisted Foundation artifacts, predecessor closure, and exact dependency closure only. It MUST_NOT require future-stage evidence.

Release final validation MUST require all applicable lifecycle and Production acceptance evidence.

<!-- SECTION_UID: WEB-GOV-02-S069 -->
## 69. Output Producer / Input Origin Binding

Every required Stage input MUST resolve to exactly one legal origin: predecessor output, persisted Foundation output, Current Authority/Project Configuration, or previous-page closure contract.

Every Stage output MUST resolve to exactly one explicit producer operation. Aggregate outputs MUST have a named compile/reconciliation operation; they MUST_NOT appear as unowned side effects of an unrelated operation.

Missing, future-stage, cyclic, duplicated, or unresolved origin/producer bindings MUST block Stage closure.

<!-- SECTION_UID: WEB-GOV-02-S070 -->
## 70. Pre-Execution Governance Load Gate

Every mutating execution item, Stage operation, Work Unit, and program-construction action MUST load governance before execution. `NO_GOVERNANCE_LOAD_RECEIPT = NO_EXECUTION`. Presence of an Implementation Manifest alone is not proof that governance was read.

The effective normative set MUST be compiled before execution from all of the following layers: (1) mandatory common governance bundles, (2) the current Stage normative bundle, (3) the registered Construction Profile normative sections when program code is involved, (4) artifact-specific normative section UIDs registered for the target, and (5) normative refs required by the exact dependency closure. Omitting any required layer is BLOCKED.

A `GOVERNANCE_LOAD_RECEIPT` MUST bind execution UID, run UID, Work Unit UID or Stage operation UID, governance revision, Root Manifest hash, effective normative set hash, resolved Section UID receipts, loaded dependency artifact UIDs/hashes, loaded acceptance blueprint UID/hash, load timestamp, and loader identity/version. Any governance/hash change invalidates the receipt and requires reload before further execution.

Execution MUST NOT begin when a required normative Section UID is missing, resolves ambiguously, points to a stale document hash, or belongs to a non-current governance revision.


A registered Construction Profile's `mandatory_contracts` MUST be materialized by the target Program Artifact instance before code write; declaration of the profile definition alone is insufficient. Missing or empty required profile contracts MUST block execution. The Program Artifact UID itself MUST already exist in the Typed Program Identity Authority with the exact canonical path, filename, owner, Work Unit, scope, profile and producer Stage that will be written.

Framework-reserved filenames require exact pre-registration authority, and each Construction Profile MUST enforce an allowed file class/extension set. A valid filename at an unregistered path, or a configuration/data file substituted for a runtime source artifact, MUST be blocked.


<!-- SECTION_UID: WEB-GOV-02-S071 -->
## 71. Product-Neutral Entity Operation Implementation / Bidirectional Coverage Gate

Implementation MUST consume the frozen product-neutral Business Entity Inventory, Operation Matrix, and Hierarchy Matrix for the exact scope. Implementation MUST_NOT invent missing entity operations, omit required operations because no control was pre-drawn, or treat an Action/Control/API count as proof of usability.

For every `REQUIRED` Business Entity operation, implementation MUST prove a bidirectional chain from user/system entry to governed outcome: `Entity Operation -> UI Control or System Trigger -> Action -> Input/Payload -> API/Command -> Runtime Owner -> Persistence/State Transition -> Feedback/Audit`, with exact registered identities for every applicable node. A system-triggered operation MAY have no visible UI only when the Operation Matrix explicitly declares a system-trigger contract and Authority.

Every visible interactive Control MUST resolve backward to exactly one allowed Business Entity operation or registered non-entity utility operation. Orphan Controls, orphan Actions, orphan Runtime endpoints, list-only child entities, create-only entities with no allowed post-create lifecycle, and edit surfaces with no version/revision disposition are blocking implementation defects.

Product-specific adapters MAY bind generic operation roles to concrete routes, schemas, providers, page identifiers, or runtimes. Those adapters MUST remain outside the common invariant definition and MUST NOT redefine the common operation semantics.

Auto-completion during implementation MUST consume the frozen `FUNCTION_ADMISSION_SCORECARD`, `AUTO_COMPLETION_SCOPE_LEDGER`, dependency closure, and `FUNCTION_VISUAL_IMPACT_MATRIX`. Implementation MUST_NOT continue recursively beyond the frozen minimal closure set. If an implementation step discovers a new dependency, Entity, permission model, persistence owner, or visual interaction pattern outside the frozen closure, execution MUST stop and return to the appropriate design Stage rather than extending scope in place.

For every automatically completed function, logic and visual delivery MUST remain atomic at the acceptance level. A user-visible functional addition is incomplete until its approved interaction entry, state representation, disabled/pending behavior, success/error/recovery feedback, and applicable version/revision visibility are implemented and testable. A visual control MUST_NOT be generated merely because a new backend capability exists; the control requires an allowed Business Entity or utility operation. Conversely, a REQUIRED user-facing operation MUST_NOT be considered complete when only UID, API, Runtime, or persistence logic exists.

Incremental construction and validation SHOULD use the registered manifest/index and reverse-dependency graph. Unchanged YAML/JSON/compiled normative content MAY be cached by exact content hash within a run, and mutation tests SHOULD use copy-on-write or in-memory overlays when physical-package integrity is not the subject of the test. Indexing MUST_NOT suppress an impacted validator. Full-package scans remain mandatory for declared integrity operations, high-pressure sweeps, index-drift audits, and Formal Freeze revalidation.


<!-- SECTION_UID: WEB-GOV-02-S072 -->
## 72. Cohesive Interaction / Conversation-Continuity Delivery

Implementation MUST consume the frozen `FUNCTIONAL_WORKBENCH_CONTRACT`, `INTERACTION_TOPOLOGY_MATRIX`, visual-topology binding, and conditional AI-interaction continuity contract when applicable. Implementation MUST_NOT independently rearrange, split, or merge functional clusters merely because the underlying Controls, Actions, APIs, Runtime owners, or components already exist.

For an `ATOMIC_WORKBENCH`, the delivered UI MUST preserve the approved operation sequence, adjacency requirements, interruption boundaries, shared-context identity, and same-surface rule. A user-visible operation chain is incomplete when its components are implemented but separated across unapproved cards, panels, page regions, tabs, routes, dialogs, or independent surfaces that break the declared journey. Responsive reflow MAY change geometry only within the approved reflow contract and MUST preserve interaction order and continuation semantics.

For an approved `CROSS_SURFACE_FLOW`, implementation MUST materialize the registered transition and context-handoff contract. The destination MUST receive the exact required entity/context/version references; a blank restart, silent loss of state, or inferred reconstruction is not a valid handoff.

For AI-assisted interaction profiles, mode changes such as single/multi-agent, discussion/comparison, resume, revision, or branch operations MUST obey the frozen identity-transition classification. Shared conversation/context state MUST NOT be duplicated into a second unregistered service or silently reset. Multi-agent execution MUST preserve the registered same-baseline request/context identity. Raw AI output MUST remain working evidence until the registered decision/formalization boundary is satisfied. Revision and branch delivery MUST preserve lineage, isolation, and explicit adoption semantics.

Logic, interaction topology, and visual grouping are one acceptance unit. A backend-complete feature with fragmented interaction topology, or a visually cohesive workbench with broken context/state continuity, is incomplete and MUST NOT be reported as delivered.
