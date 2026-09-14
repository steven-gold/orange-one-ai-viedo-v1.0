---
document_id: WEB-GOV-03
version: 2.1.0
order: 3
category: execution_control
required_before_execution: true
requires: WEB-GOV-01, WEB-GOV-02
status: normative
permanent_inheritance: true
---

# 03 AI 施工工作紀律、防呆、防重複、防雙軌與持續執行規範

<!-- SECTION_UID: WEB-GOV-03-S000 -->
## 0. 規範目的

本文件管理 AI 在施工期間「如何工作」。

目標是防止：

- 同時開多個未完成工作。
- 這裡做一點、那裡做一點。
- 建立第二套系統。
- 同義重複建檔。
- 新舊 Runtime 同時生效。
- 同一概念存在多個 Owner。
- 中斷後重複執行 Effectful Operation。
- 只做分析、盤點或回報，未真正施工。
- 每完成一小步就停止等待使用者再次要求繼續。

<!-- SECTION_UID: WEB-GOV-03-S001 -->
## 1. 最高工作原則

AI MUST 遵守：

- ONE ACTIVE PRIMARY WORK UNIT
- ONE CLEAR START POINT
- ONE CLEAR END POINT
- ONE DEFINITION OF DONE
- ONE CANONICAL OWNER
- ONE VERIFIED CLOSURE
- CLOSE BEFORE MOVING
- SEARCH BEFORE CREATE
- VERIFY BEFORE CLAIMING
- NO PARALLEL SYSTEM
- NO SILENT CONFLICT

<!-- SECTION_UID: WEB-GOV-03-S001A -->
## 1A. 永久執行繼承規則

本工作紀律 MUST 對專案後續所有工作永久生效，不因新對話、新代理、新版本、新分支或新 Change Request 而失效。

每輪開始 MUST 先確認：

- 四份治理規範仍為 Current Governance Standard。
- Current Canonical Authority。
- Current Revision。
- Active Work Unit。
- Current Owner Mapping。
- Current Resume Point。
- Current Audit / Evidence State。

AI MUST_NOT 因 Context 中斷重新發明架構、命名、Owner、Runtime 或驗收標準。

既有 Owner 存在時，預設行為是 PATCH EXISTING OWNER，而不是建立平行新檔。

<!-- SECTION_UID: WEB-GOV-03-S002 -->
## 2. Work Unit

每個正式 Work Unit MUST 具備：

- Work Unit UID
- Canonical Name
- Scope
- Out-of-Scope
- Owner Files
- Dependencies
- Start Condition
- Definition of Done
- Required Audit Items
- Required Tests
- Required Evidence
- Current Status
- Resume Point

<!-- SECTION_UID: WEB-GOV-03-S003 -->
## 3. 單一主要施工單位

正常情況同一時間只能有一個 `ACTIVE_PRIMARY_WORK_UNIT`。

目前 Work Unit 在無真正 Blocker 的情況下 MUST 完成 Closure，再進入下一個無關 Work Unit。

MUST_NOT 採用：

- 多個 Page 同時只做 UI。
- 多個 Runtime 同時只做 Skeleton。
- 多個 Module 同時各做部分功能。
- 以「先鋪框架」為理由留下大量未閉環項目。

<!-- SECTION_UID: WEB-GOV-03-S004 -->
## 4. Vertical Closure

Work Unit SHOULD 依垂直閉環方式施工：

`Entry -> UI -> Control -> Action -> Validation -> Permission -> Runtime -> Data/Provider -> Audit -> Response -> Feedback -> Test -> Evidence -> Closure`

只要上列節點是該 Work Unit REQUIRED，就不得省略。

<!-- SECTION_UID: WEB-GOV-03-S005 -->
## 5. PRE_IMPLEMENTATION_DUPLICATE_GUARD

建立或修改前 MUST 搜尋：

- Canonical UID
- Canonical Name
- Aliases
- Deprecated Names
- Naming Registry
- Owner Registry
- Existing Files
- Existing Symbols
- Existing Routes / Endpoints
- Existing Runtime
- Existing Data Objects
- Existing Permissions
- Existing Tests
- Existing Migrations

第一次搜尋不到 MUST_NOT 直接判定不存在。

<!-- SECTION_UID: WEB-GOV-03-S006 -->
## 6. Duplicate-by-Renaming Guard

同一概念如果只是名稱不同，MUST 視為同一候選治理單位並先 Resolve Canonical Identity。

AI MUST_NOT 因：

- 字序不同
- 同義字不同
- 語言不同
- 顯示名稱不同
- 檔名不同

就建立第二正式項目。

<!-- SECTION_UID: WEB-GOV-03-S007 -->
## 7. SECOND_SYSTEM_GUARD

施工前與施工後 MUST 檢查是否產生第二套：

- Authority
- Navigation
- Page Registry
- Component Owner
- API / Entry
- Runtime
- Data Truth
- Permission System
- State Machine
- External Adapter
- Audit Standard

如兩套同功能且皆可正式生效，MUST 標示：

`SECOND_SYSTEM_FAIL`

並停止相關 Release。

<!-- SECTION_UID: WEB-GOV-03-S008 -->
## 8. Canonical Owner Guard

每個 Capability MUST 有唯一 Canonical Owner。

如發現兩個以上 Owner Claim，AI MUST：

1. 讀取 Authority。
2. 讀取 Naming Registry。
3. 檢查正式 Reference。
4. 檢查 Runtime Usage。
5. 檢查 Production Usage（如已部署）。
6. 裁決 Canonical Owner。
7. 將其他來源移除、Deprecated 或降級為非正式資料。
8. 再繼續施工。

MUST_NOT 再新增第三 Owner。

<!-- SECTION_UID: WEB-GOV-03-S009 -->
## 9. Conflict Guard

至少 MUST 檢查：

- Authority Conflict
- Naming Conflict
- UID Conflict
- Owner Conflict
- Route Conflict
- Design Conflict
- Action Conflict
- API Conflict
- Runtime Conflict
- Data Conflict
- Permission Conflict
- State Conflict
- Migration Conflict
- Version Conflict

Critical Conflict 未裁決不得繼續 Effectful Deployment。

<!-- SECTION_UID: WEB-GOV-03-S010 -->
## 10. Legacy Guard

Legacy Artifact MUST 明確標示：

- `ACTIVE`
- `DEPRECATED`
- `READ_ONLY`
- `MIGRATING`
- `REMOVED`

Legacy 與 Current MUST_NOT 同時無治理地執行相同 Effectful Capability。

已淘汰入口 SHOULD Fail Closed 或不可達。

<!-- SECTION_UID: WEB-GOV-03-S011 -->
## 11. Dual-write Guard

如系統未正式定義 Dual-write，MUST_NOT：

- 同一 Operation 寫入兩個互相競爭的 Truth Store。
- Current Runtime 與 Legacy Runtime 同時寫相同 Business Entity。

如正式需要 Dual-write，MUST 定義：

- Primary Truth
- Secondary Target
- Sync Direction
- Consistency Rule
- Failure Handling
- Cutover Condition
- Exit Condition

<!-- SECTION_UID: WEB-GOV-03-S012 -->
## 12. Orphan Guard

施工後 MUST 檢查：

- Page without Entry
- Control without Action
- Action without Runtime
- Runtime without Owner
- Runtime without Test
- API without Permission
- Data Object without Owner
- Permission without Enforcement
- Asset without Reference
- Test without Capability
- Evidence without Revision

Critical Orphan 不得進入 Release Candidate。

<!-- SECTION_UID: WEB-GOV-03-S013 -->
## 13. Dead Code Guard

施工完成後 MUST 判斷舊：

- Component
- Route
- API
- Runtime
- Adapter
- Permission
- Mapping
- Data Object

是否仍有正式 Reference。

無 Reference 的正式舊路徑 MUST 依治理規則標示 `DEPRECATED`、`READ_ONLY` 或 `REMOVED`。

<!-- SECTION_UID: WEB-GOV-03-S014 -->
## 14. Stub Guard

以下內容 MUST_NOT 進入 Production Ready：

- TODO in Required Flow
- Placeholder Runtime
- No-op Handler
- Hardcoded Success
- Fake Response
- Fake Provider
- Temporary Allow-all
- Temporary Security Bypass
- Mock Session in Production Path
- Mock Data Store in Production Path

測試用 Mock MUST 明確隔離並標示 `MOCK_ONLY`。

<!-- SECTION_UID: WEB-GOV-03-S015 -->
## 15. 新檔建立前防呆

AI 建立任何正式檔案前 MUST 回答：

- 是否已有相同 UID？
- 是否已有同義 Alias？
- 是否已有 Canonical Owner？
- 是否只是修改既有功能？
- 是否真的具有獨立治理生命週期？
- 正式 Folder 是什麼？
- 正式 File Name 是什麼？
- 是否會產生第二套？

任一問題未解析不得建檔。

<!-- SECTION_UID: WEB-GOV-03-S016 -->
## 16. POST_IMPLEMENTATION_DUPLICATE_GUARD

每輪施工後 MUST 重新搜尋本輪新增或修改的：

- File
- Symbol
- Route / Endpoint
- Runtime
- Data Object
- Permission
- Migration Intent
- Test Owner

確認未產生平行正式版本。

<!-- SECTION_UID: WEB-GOV-03-S016A -->
## 16A. Content Bloat / Mixed File / Residual Guard

施工前後 MUST 額外執行：

### Content Bloat Guard

檢查是否因施工產生：

- 完整 Payload 跨資料夾複製
- Registry 複製 Owner 全文
- Evidence 複製 Authority 全文
- Runtime / Integration / Security 互相複製同一 Implementation
- 同內容因重新命名形成多份正式檔

### Mixed File Guard

檢查一個檔案是否同時承擔多個獨立治理生命週期。

結果只能是：

- `SPLIT_REQUIRED`
- `MIXED_ALLOWED`

不得保留未裁決的 Critical Mixed Owner。

### Residual File Guard

完成 Work Unit 前 MUST 清除無正當用途的：

- temp
- backup
- copy
- old
- abandoned split
- unused ref
- dead owner
- dead implementation
- empty placeholder
- obsolete intermediate artifact

完成要求：

- `CRITICAL_DUPLICATE = 0`
- `UNRESOLVED_CRITICAL_MIXED_FILE = 0`
- `UNJUSTIFIED_RESIDUAL_FILES = 0`

刪除前 MUST 檢查 Reference、Import、Runtime、Test、Build 與 Historical Retention Dependency。

<!-- SECTION_UID: WEB-GOV-03-S017 -->
## 17. Gap Handling

施工發現直接屬於目前 Work Unit 的必要缺口時 MUST 當場納入 Closure。

MUST_NOT 使用：

- 後續再補
- 先跳過
- 下一輪再做
- 先做其他頁

來逃避目前 Work Unit 的 Required Gap。

<!-- SECTION_UID: WEB-GOV-03-S018 -->
## 18. 合法 Blocker

只有明確無法由目前施工直接解除的條件可標 `BLOCKED`，例如：

- External Credential Required
- External Account Required
- Human Approval Required
- Authority Decision Required
- Platform Restriction
- Upstream Required Dependency Missing

BLOCKED MUST 記錄：

- Blocker UID
- Scope
- Severity
- Reason
- Impact
- Unlock Condition
- Completed Gates
- Missing Gates
- Exact Resume Point

<!-- SECTION_UID: WEB-GOV-03-S019 -->
## 19. Blocked Item 不得消失

Blocked Work Unit MAY 暫時讓位給不依賴它的下一個 Work Unit，但 MUST 保存在 Blocker Ledger，直到：

- RESOLVED
- REMOVED_FROM_SCOPE
- SUPERSEDED_BY_AUTHORITY

<!-- SECTION_UID: WEB-GOV-03-S020 -->
## 20. Scope Freeze

Work Unit 開始後 Scope SHOULD Freeze。

只有完成該 Work Unit 必需的直接 Dependency Gap 可以納入。

新的改善、延伸功能或非必要需求 MUST 進 Future Scope，避免無限擴張。

<!-- SECTION_UID: WEB-GOV-03-S021 -->
## 21. 優先級

工作 SHOULD 依以下順序處理：

1. Blocking Dependency
2. Critical Path
3. Core Business Flow
4. Dependent Capability
5. Secondary Capability
6. Optimization

高嚴重度未閉環時 SHOULD_NOT 大量投入純美化或非必要優化。

<!-- SECTION_UID: WEB-GOV-03-S022 -->
## 22. Foundation Closure

共用 Foundation 如被多個 Work Unit 依賴，MUST 先做到自己的 Definition of Done。

MUST_NOT 只建立 Interface、Skeleton、Empty Class、Empty Handler 或 Placeholder 就宣稱 Foundation 完成。

<!-- SECTION_UID: WEB-GOV-03-S023 -->
## 23. Correct -> Complete -> Verify -> Optimize

固定順序 SHOULD 為：

1. Correct
2. Complete
3. Verify
4. Stabilize
5. Optimize

核心閉環未完成前不得以大量非必要優化取代完工。

<!-- SECTION_UID: WEB-GOV-03-S024 -->
## 24. Execution Loop

每個 Active Work Unit MUST 使用：

`IMPLEMENT -> VERIFY -> FIX -> REVERIFY`

直到 Current Required Gate PASS。

發現 FAIL 後 MUST_NOT 立即跳往無關功能。

<!-- SECTION_UID: WEB-GOV-03-S025 -->
## 25. Closure Check

離開 Work Unit 前 MUST 檢查：

- Required Implementation 完整。
- Required Dependency 完整。
- Runtime 真正接通。
- Data / Provider 真正接通。
- Permission 真正 Enforcement。
- Error Path 已處理。
- Required Tests PASS。
- Required Regression PASS。
- Evidence 已綁定。
- Duplicate Guard PASS。
- Second-System Guard PASS。
- Conflict Guard PASS。
- Orphan Guard PASS。
- Stub Guard PASS。
- Direct Gap = 0。

任何 REQUIRED 條件失敗，Work Unit MUST_NOT `CLOSED`。

<!-- SECTION_UID: WEB-GOV-03-S026 -->
## 26. 禁止先關單再補

MUST 遵守：

`IMPLEMENT -> TEST -> AUDIT -> EVIDENCE -> CLOSURE -> CLOSED -> NEXT`

MUST_NOT：

`IMPLEMENT -> CLOSED -> LATER_FIX`

<!-- SECTION_UID: WEB-GOV-03-S027 -->
## 27. Batch Governance

大型任務 MAY 拆成 Batch，但每個 Batch MUST 有：

- Batch UID
- Scope
- Affected UIDs
- Definition of Done
- Implementation
- Required Tests
- Duplicate / Conflict Guards
- Evidence
- Closure State

Batch MUST 用來累積 Closed Work Units，而不是累積半成品。

<!-- SECTION_UID: WEB-GOV-03-S028 -->
## 28. Commit / Revision Boundary

每個完整 Work Unit 或合理 Batch SHOULD 對應清楚 Source Revision Boundary。

Revision Description MUST 指向 Canonical Scope 與 Change Purpose。

MUST_NOT 使用無法理解內容的模糊 Revision Description。

<!-- SECTION_UID: WEB-GOV-03-S029 -->
## 29. Resume Ledger

長任務 MUST 維持 Resume Ledger，至少包含：

- Current Work Unit UID
- Current Source Revision
- Current Owner
- Current Step
- Last Successful Gate
- Last Failed Gate
- Current Blocker
- Pending Tests
- Pending Deployment
- Exact Next Action

新執行不得依賴 AI 臨時記憶猜斷點。

<!-- SECTION_UID: WEB-GOV-03-S030 -->
## 30. Context Recovery

恢復施工 MUST：

1. Resolve Current Source。
2. Resolve Current Revision。
3. Read Resume Ledger。
4. Verify Last Completed Effectful Action。
5. Resolve Active Work Unit。
6. Run Duplicate Guard。
7. Run Conflict Guard。
8. Continue Exact Next Action。

MUST_NOT 因對話中斷重新規劃整個專案。

<!-- SECTION_UID: WEB-GOV-03-S031 -->
## 31. Idempotent Execution

可安全重試的操作 SHOULD 設計為 Idempotent。

Effectful Retry 前 MUST 確認前一次是否已成功，特別是：

- Create
- Publish
- Approve
- Lock
- Send
- Charge
- Generate
- Migration Apply

MUST_NOT 因中斷直接重送可能產生重複副作用的操作。

<!-- SECTION_UID: WEB-GOV-03-S032 -->
## 32. Continuous Execution Mode

`CONTINUOUS_EXECUTION_MODE` 是工作流程政策，不代表任何執行環境必然支援背景持續運算。

當以下條件成立：

- Scope 明確。
- Authority 明確。
- Active Work Unit 明確。
- 下一步可判定。
- 無需要人工裁決的衝突。
- 無外部 Blocker。

AI SHOULD 自動從目前 Step 持續執行下一個 REQUIRED Step，直到：

- Active Work Unit CLOSED；或
- 指定 Scope 全部 CLOSED；或
- 遇到正式停止條件。

AI SHOULD_NOT 每完成一個小步驟就要求使用者重新輸入「繼續」。

<!-- SECTION_UID: WEB-GOV-03-S033 -->
## 33. Progress Update 不等於停止

中途進度訊息只代表狀態回報。

`PROGRESS_UPDATE != EXECUTION_STOP`

若執行環境仍允許且沒有停止條件，AI SHOULD 繼續目前 Active Work Unit。

<!-- SECTION_UID: WEB-GOV-03-S034 -->
## 34. Background Execution Truth Rule

只有執行平台明確提供並已啟動持久或背景工作能力時，AI 才可以宣稱 Background Execution 正在進行。

如無實際背景執行能力，AI MUST_NOT 宣稱：

- 正在背景持續施工。
- 回覆結束後仍會自行繼續。
- 稍後會自動完成目前工作。

背景執行狀態 SHOULD 可追溯：

- Job / Task ID
- Current State
- Trigger
- Last Run
- Next Run / Condition（如適用）

<!-- SECTION_UID: WEB-GOV-03-S035 -->
## 35. Scheduled / Event-driven Execution

如平台支援，定時或事件式執行 MAY 用於：

- 狀態重查
- Gate Verification
- Deployment Verification
- Health Monitoring
- Condition Watch
- Resume Trigger

MUST_NOT 將不具備完整專案上下文與寫入能力的排程任務假裝成主要 Implementation Runtime。

<!-- SECTION_UID: WEB-GOV-03-S036 -->
## 36. 背景工作不得降低 Gate

Foreground、Background、Scheduled、Event-triggered 執行都 MUST 遵守相同：

- Authority
- Naming
- Duplicate Guard
- Conflict Guard
- Definition of Done
- Audit Matrix
- Evidence
- Production Gates

<!-- SECTION_UID: WEB-GOV-03-S037 -->
## 37. 強制停止條件

遇到以下任一狀態 MUST 停止對應高風險或不可判定操作：

- `AUTHORITY_CONFLICT`
- `NAMING_CONFLICT`
- `SECOND_SYSTEM_CONFLICT`
- `DESTRUCTIVE_OPERATION_UNCERTAIN`
- `SECRET_REQUIRED`
- `USER_DECISION_REQUIRED`
- `EXTERNAL_APPROVAL_REQUIRED`
- `PLATFORM_BLOCKED`

停止時 MUST 寫入 Resume Ledger。

<!-- SECTION_UID: WEB-GOV-03-S038 -->
## 38. 非必要確認不得阻塞

若下列工作原本已屬 Definition of Done，AI SHOULD 直接執行而非反覆詢問：

- Required Test
- Required Regression
- Direct Dependency Repair
- Required Audit Update
- Required Build Verification

<!-- SECTION_UID: WEB-GOV-03-S039 -->
## 39. 歷史 PASS 不等於現在 PASS

任何共用 Owner、Dependency 或 Runtime 修改後 MUST 分析 Impact Scope。

受影響的歷史 PASS MUST 進 `REVERIFY_REQUIRED`。

<!-- SECTION_UID: WEB-GOV-03-S040 -->
## 40. 完成度不得以活動量計算

MUST_NOT 以：

- File Count
- Line Count
- Commit Count
- Message Count
- UI Screenshot Count

作為主要完成度。

完成度 MUST 由 Closed Work Units 與 Passed Required Gates 計算。

<!-- SECTION_UID: WEB-GOV-03-S041 -->
## 41. 空轉禁止

以下屬於前置或驗證工作，不得單獨宣稱 Implementation 完成：

- Read
- Search
- Inspect
- Compare
- Audit
- Plan
- List

施工成果 MUST 有對應實際：

- Modify
- Implement
- Migrate
- Test
- Build
- Deploy
- Verify

<!-- SECTION_UID: WEB-GOV-03-S042 -->
## 42. 虛假完成禁止

- 無 Source Change / Required Artifact，不得說已施工。
- 無 Test Result，不得說已驗證。
- 無 Migration Result，不得說資料結構已套用。
- 無 Deployment Result，不得說已部署。
- 無 Production Evidence，不得說正式可使用。

<!-- SECTION_UID: WEB-GOV-03-S043 -->
## 43. 每輪開始固定動作

每輪施工 MUST：

1. Resolve Current Source。
2. Resolve Current Revision。
3. Read Resume Ledger。
4. Resolve Active Work Unit。
5. Read Definition of Done。
6. Read Acceptance Matrix。
7. Run Duplicate Guard。
8. Run Conflict Guard。
9. Continue Current Work。

<!-- SECTION_UID: WEB-GOV-03-S044 -->
## 44. 每輪結束固定回報

至少 MUST 回報：

- Active Work Unit
- Canonical UID
- Current Source Revision
- Actual Modifications
- Tests Executed
- PASS / FAIL
- Duplicate Guard
- Second-System Guard
- Conflict Guard
- Orphan Guard
- Current Gate
- Closure State
- Blocker
- Exact Resume Point



<!-- SECTION_UID: WEB-GOV-03-S044A -->
## 44A. No Midstream Pilot Rule

用於驗證治理規範是否真的可運作的 Pilot MUST 從最初 Raw Source Intake 開始。

MUST_NOT 選擇一個已完成 Blueprint、已完成 UI 或已存在大量 Implementation 的頁面，然後只從中間補測並宣稱「從設計到上線流程已驗證」。

Pilot Evidence MUST 能逐步指出：

`Raw Source -> Classification -> Canonical Owner -> Blueprint -> Visual -> Freeze -> Implementation -> Tests -> Build -> Deployment -> Production Render -> Closure`

每一段 MUST 有 Revision/Evidence Boundary。

<!-- SECTION_UID: WEB-GOV-03-S044B -->
## 44B. Auto-remediation Discipline

自動修補器 MUST 先輸出 Gap Classification，再決定是否可修改。

只有下列狀態可自動修改：

- `AUTO_REMEDIABLE`
- Authority 唯一明確的 `IMPLEMENTATION_GAP`
- 規格已 Frozen 的 `LEVEL_1_MICRO` Visual Geometry 修正
- 可由 Current Owner 唯一重算的 Derived Metric / Hash / Summary

以下 MUST_NOT 自動修改：

- `AUTHORITY_GAP`
- `ARCHITECTURE_GAP`
- `INPUT_SOURCE_GAP` 且來源不唯一
- 多個合理 Next Step
- 多個合理 Permission Projection
- 多個合理 State Transition
- 需要產品決策的 UI / Flow

自動修補完成後 MUST 回到原 Gap 的上一 Gate 重新驗證，禁止只跑新增 Test。

<!-- SECTION_UID: WEB-GOV-03-S044C -->
## 44C. Complexity-invariant Execution

AI 對 P1～P6 Page Complexity Profile MUST 使用同一 Execution Loop 與 Closure 規則。

差異只允許存在於正式 `NOT_APPLICABLE` 項目，不得出現：

- 簡單頁少走 Source Truth Gate。
- 複雜頁因功能太多而只抽樣 Control。
- 跨頁 Flow 只驗 Source Page。
- Async/External Page 因 Provider 尚未配置就把 Required Item 移出分母。

<!-- SECTION_UID: WEB-GOV-03-S044D -->
## 44D. Production Sync Failure Handling

若部署平台成功但正式網址仍是舊頁面，MUST 視為 Release Failure，而不是視覺小問題。

AI MUST 依序定位：

1. Source Revision 是否正確。
2. Build 是否由該 Revision 產生。
3. Deployment 是否使用該 Build。
4. Production Runtime Identity 是否對齊。
5. Route / Asset Manifest 是否對齊。
6. CDN / Edge / Browser Cache 是否仍供應舊 Asset。
7. Production DOM Fingerprint 是否仍為舊版。
8. Production Visual Geometry / Screenshot 是否仍為舊版。

只有定位到單一 Root Cause 後才 MAY 修復，禁止因看到舊畫面就直接重新部署或重做頁面。

<!-- SECTION_UID: WEB-GOV-03-S045 -->
## 45. 文件完成條件

本規範持續有效，直到所有正式 Scope Work Units Closed 與 Final Production Acceptance PASS。


<!-- SECTION_UID: WEB-GOV-03-S047 -->
## 47. v2.1.0 No Midstream Pilot Rule

用來驗證治理規範本身的正式 Pilot MUST 從 Source Intake / Classification / Repository Placement 開始，不得從已完成 Blueprint、現有 React Page 或 Runtime 中段開始後宣稱完整生命週期 PASS。

Pilot MUST 保存每一 Gate 的輸入、輸出、Evidence、`run_uid` 與 Exact Next Action。

<!-- SECTION_UID: WEB-GOV-03-S048 -->
## 48. v2.1.0 Safe Auto-Remediation Boundary

自動補齊 MUST 針對「功能前後步驟」而非 UI 元件數量。

只有 Authority 已明確指定 Implementation、或前後 Contract 唯一可推導且沒有第二種合理產品行為時，才可 `AUTO_REMEDIABLE`。

兩種以上合理設計、缺 Authority、缺 Architecture/Transport/Permission Contract、或 Required Production Capability 尚 fail-closed 時 MUST BLOCK，AI MUST_NOT 為讓 Gate 變綠而發明 Default、API、Runtime、State、Provider、按鈕或下一步。

<!-- SECTION_UID: WEB-GOV-03-S049 -->
## 49. v2.1.0 N/A Authority Rule

任何 `NOT_APPLICABLE` MUST 綁 Authority Applicability Evidence。Test Fixture、執行者主觀判斷、空陣列或缺檔 MUST_NOT 自行形成 N/A。

Cross-page Flow、Provider、Deployment、State Machine、Field Identity 等 Gate 均套用本規則。

<!-- SECTION_UID: WEB-GOV-03-S050 -->
## 50. v2.1.0 Version Numbering Rule

本治理套件自本版起使用 `v2.1.0` 系列。更新優先遞增第三位：`v2.1.1` → ... → `v2.1.9`；第三位已為 9 的下一個更新 MUST 進位為 `v2.2.0`，MUST_NOT 建立 `v2.1.10`。


## v2.1.0 Pilot Hardening — Shared Owner / Port Resolution

- Effectful functional-chain validation MUST distinguish page-local execution from `SHARED_OPERATION_REFERENCE`, `SOURCE_INTEGRATION_PORT`, `COMPOSITE_TO_EXISTING_EXECUTE_PORT`, and equivalent registered owner bindings.
- A shared owner reference MUST_NOT be treated as a missing page-local API/runtime. The validator MUST resolve the exact owner + operation/port reference before opening an implementation gap.
- AI MUST_NOT create a duplicate API, runtime, repository, database owner, or provider adapter merely because the page authority delegates execution to a shared owner.
- `NOT_APPLICABLE` for page-local transport/data nodes is legal only when exact shared-owner Authority evidence explains where that responsibility is owned.

<!-- SECTION_UID: WEB-GOV-03-S046 -->
## 46. Governance Specification Development / Test Lock Discipline

`v2.1.0` is the immutable baseline for the current governance repair cycle. The original baseline package and its checksums MUST remain unchanged.

A governance working candidate MAY be created from that baseline only to repair a reproduced governance defect. Experimental changes from prior candidates MUST_NOT be silently carried forward unless each change is independently justified by a recorded defect against the baseline.

Each governance test stage MUST have a `GOVERNANCE_STAGE_LOCK` with at least: baseline version/hash, stage UID, allowed defect UIDs, candidate normative hash, test run UID, lock state, start timestamp, end timestamp, and next-stage eligibility.

When a stage enters `TEST_FROZEN`, normative governance files are read-only for that test run. If their aggregate hash changes before run closure, the test result MUST be `INVALIDATED_SPEC_MUTATED_DURING_TEST`, regardless of individual test outcomes.

Test fixtures MUST contain observable facts only. They MUST_NOT carry validator-consumed expected outcomes such as `should_fail`, `expected_status`, precomputed blocker totals, or equivalent instructions that tell the validator what conclusion to return. Expected results belong only in the external test harness after validator execution.

Self-declared `PASS`, `COMPLETE`, `LOCKED`, or zero-error counters inside the fixture MUST NOT override facts recomputed by the validator.

A reproduced defect MUST follow this sequence:

`TEST_FROZEN -> RUN_FAIL -> DEFECT_RECORDED -> BUGFIX_WINDOW_OPEN -> PATCHED_CANDIDATE -> RETEST_REQUIRED -> TEST_FROZEN`

A successful stage MUST follow:

`TEST_FROZEN -> RUN_PASS -> STAGE_RELEASE_LOCKED`

Once `STAGE_RELEASE_LOCKED`, the released rule content MUST_NOT be edited. A later defect opens a new candidate/version; it does not reopen or mutate the locked release.

During governance validation, product-specific page/application data MAY be used only as empirical test/reference input. Product identity MUST_NOT become a normative dependency of the common governance rules. Formal governed implementation is forbidden until governance release state is `FINAL_LOCKED_FOR_WEBSITE_RECONSTRUCTION` or the equivalent release state registered by the adopting system.

<!-- SECTION_UID: WEB-GOV-03-S051 -->
## 51. Stage-1 Retry / Relock Execution Control

When a locked Stage-1 release reveals a reproduced governance defect, the locked release remains immutable. A new bugfix candidate MUST be created from that locked release and may change only the reproduced defect scope.

For a Source-to-Blueprint retry, execution order is fixed:

`EMPTY_CURRENT_TEST_WORKSPACE -> RAW_SOURCE_REFERENCE -> DOMAIN_EXTRACTION -> RESPONSIBILITY_CLASSIFICATION -> CLASSIFICATION_VALIDATION -> BASE_BLUEPRINT_COMPILE -> BLUEPRINT_VALIDATION -> CLEAN_SCAN -> RUN_CLOSE`

The executor MUST_NOT:

- reuse prior-run Current extraction/classification/blueprint outputs;
- skip directly from Raw Source to Base Blueprint;
- treat a domain-level mixed artifact as a final responsibility owner;
- mutate normative rules while a run is active;
- patch a failing fixture to manufacture PASS;
- leave previous-run output in the Current Test Workspace.

A retry run MUST bind: immutable source refs/hashes, candidate normative hash, run UID, output root, and clean-start evidence before extraction begins.

If the candidate rules are changed, the active run is invalid and MUST be restarted from an empty Current Test Workspace under a new run UID and new candidate hash.

<!-- SECTION_UID: WEB-GOV-03-S052 -->
## 52. Source Enumeration Before Classification / Dual-Blueprint Compile Order

Stage-1 execution order is refined to:

`EMPTY_CURRENT_TEST_WORKSPACE -> RAW_SOURCE_REFERENCE -> SOURCE_STRUCTURE_ENUMERATION -> SOURCE_SEGMENT_MAPPING -> SOURCE_FACT_MATERIALIZATION -> DOMAIN_EXTRACTION -> RESPONSIBILITY_CLASSIFICATION -> PAGE_BASE_BLUEPRINT -> VISUAL_BASE_BLUEPRINT -> BLUEPRINT_BINDING -> CLEAN_SCAN -> RUN_CLOSE`

`SOURCE_STRUCTURE_ENUMERATION` is a required independent observation step. Classification code MUST consume its node UIDs; it MUST_NOT silently define its own smaller source universe.

Page and Visual Base Blueprint compilation are separate work units. Neither may read the other domain's classified payload. Binding occurs only after both blueprint hashes are available.

`SOURCE_FACT_MATERIALIZATION` is the only legal phase immediately after a closed `SOURCE_SEGMENT_MAPPING`. Starting Source Fact Materialization after Segment Mapping completion MUST_NOT be treated as a Segment Mapping boundary violation. The Source Fact phase consists of `SOURCE_CONTEXT_COMPILATION`, `SOURCE_SUPERSESSION_CONFLICT_RESOLUTION`, and `SOURCE_DEPENDENCY_EXTRACTION`; all required Source Fact artifacts MUST close before Domain Extraction, Responsibility Classification, or Base Blueprint work may start. Website construction and deployment remain forbidden in Stage-01.

A predecessor-stage validator MUST validate the predecessor's closure invariants without permanently forbidding the registered legal successor phase. A successor may start only after its predecessor closes, and a later phase may not be used to retroactively invalidate an otherwise valid predecessor merely because the registered successor has begun. Illegal skipping remains fail-closed.

A predecessor validator MUST_NOT require the global Current phase/state to remain exactly equal to the predecessor terminal state after a registered legal successor begins, and MUST_NOT require a successor-started flag to remain false as a permanent acceptance condition. It MUST instead validate the predecessor closure facts, immutable proof identities, exact unresolved-Authority identity, and terminal receipt that it owns. Registered phase-order legality is owned by the Phase Boundary Gate. An unregistered successor, stage skip, predecessor completion reversion, proof loss, Authority identity drift, or terminal-receipt drift remains blocking. Every registered predecessor→successor edge MUST have regression coverage proving both legal-successor acceptance and illegal-skip rejection.


Raw Source Capture is a separately closable sub-step before `SOURCE_STRUCTURE_ENUMERATION` and MUST obey all of the following:

- the capture terminal state MUST be exactly `CAPTURE_CLOSED` before enumeration may start;
- the only legal next-step identity is exactly `SOURCE_STRUCTURE_ENUMERATION`; aliases such as classification, structure classification, or free-text equivalents MUST_NOT satisfy the gate;
- a source that contains both Page Construction and Visual Construction facts MUST use the neutral role `MIXED_PAGE_VISUAL_SOURCE_INPUT` until segment-level classification; it MUST_NOT be pre-labelled `PAGE_SOURCE_INPUT` or `VISUAL_SOURCE_INPUT`;
- the Raw Source directory MUST contain source bytes only. Manifests, binding records, README/NOTICE files, status records, evidence metadata, and any generated control artifact MUST live outside the Raw Source directory;
- the Raw Source physical file set MUST exactly equal the target paths registered by the Raw Source Reference Manifest; any extra or missing file MUST block the stage;
- closing Raw Source Capture freezes its captured source bytes for that run. Re-capture requires a new clean retry/run; an already closed capture MUST_NOT remain writable.

### Cross-Lifecycle Semantic Granularity / Mixed Terminal Unit Guard

The syntax tree, file hierarchy, JSON/YAML indentation level, DOM nesting level, contract object boundary, runtime module boundary, test grouping, deployment grouping, or audit row boundary MUST_NOT by itself be treated as governance granularity. Governance granularity is semantic and responsibility-based.

For every Stage-01 through Stage-11 operation, any candidate terminal unit MUST be semantically homogeneous for its current governance responsibility. If one candidate terminal unit contains responsibilities that differ in Owner, Lifecycle, Approval, Version, Test/Acceptance Scope, Planning Domain, Release Identity, Rollback Identity, Applicability, or Closure Identity, that unit is a mixed terminal unit and MUST be recursively decomposed before the current Stage may close.

The only exception is explicit `MIXED_ALLOWED` evidence proving all applicable responsibility dimensions share the same Owner, Lifecycle, Approval, Version, Test/Acceptance Scope and current-stage identity. Convenience, syntax nesting, file size, implementation proximity, or AI-generated grouping MUST_NOT satisfy `MIXED_ALLOWED`.

Every Stage close MUST prove all of the following for the units governed by that Stage:

- `MIXED_TERMINAL_UNITS = 0`;
- `UNRESOLVED_CONTAINER_UNITS = 0`;
- recursive decomposition preserves every required parent/child responsibility with no lost, duplicate, or multiply-owned responsibility;
- downstream mapping consumes the final terminal-unit UIDs rather than redefining a smaller semantic universe;
- a later Stage MUST re-run the same semantic-granularity check on its own terminal units; an earlier Stage PASS does not waive later-stage granularity validation.

Stage-specific terminal-unit identities are registered in `GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml` and this rule is loaded through the common governance bundle for every Stage.



<!-- SECTION_UID: WEB-GOV-03-S053 -->
## 53. Universal Supersession / Cleanup Transaction

Supersession is a transaction, not a metadata label. The rule applies to every Current artifact class, not only Source Intake.

The mandatory order is:

`REGISTER_REPLACEMENT -> RESOLVE_FORWARD_REFERENCES -> RESOLVE_REVERSE_DEPENDENCIES -> MARK_IMPACTED_CONSUMERS_REVERIFY_REQUIRED -> PROVE_ZERO_CURRENT_REFERENCE_TO_SUPERSEDED_OWNER -> REMOVE_SUPERSEDED_FROM_CURRENT_INDEX -> DELETE_GENERATED_DUPLICATE/TEMP/BACKUP/OBSOLETE_ARTIFACTS -> UPDATE INDEXES -> UPDATE CLEANUP_LEDGER -> ORPHAN/RESIDUAL/BROKEN_REFERENCE_SCAN`

Raw Source MAY remain as immutable historical/reference evidence, but MUST_NOT remain a Current Owner after supersession.

A stage cannot close while any of the following is non-zero: Current reference to superseded owner, duplicate Current owner, orphan required artifact, unjustified residual file, broken reference.

<!-- SECTION_UID: WEB-GOV-03-S054 -->
## 54. Index / Hash / Lazy-Load Execution Rule

Every execution stage MUST use index-first loading. A Work Unit resolves its registered manifest, then exact artifact refs, then dependency closure. Re-reading the full governance package or all page construction files for an ordinary local change is forbidden.

Changed hashes invalidate only the affected reverse dependency closure unless a shared/global owner change explicitly requires wider revalidation.

Index maintenance MUST be atomic with artifact mutation. Creating a file without updating the Artifact Index, Dependency Index, Reverse Dependency Index and applicable Cleanup/Supersession records is an incomplete mutation and MUST FAIL the stage.
<!-- SECTION_UID: WEB-GOV-03-S055 -->
## 55. Protected Current Artifact / Safe Cleanup Delete Gate

Automated cleanup MUST be fail-closed. A file MUST_NOT be deleted merely because its name appears stale, duplicated, old, final, backup-like, or unreferenced by a partial scan.

Before deleting any artifact, cleanup MUST prove all of the following:

- artifact is not listed as a protected Current governance artifact;
- artifact is not a Raw Source immutable reference;
- Current owner/index reference count is zero;
- reverse dependency count is zero or all dependents have migrated and are `REVERIFY_REQUIRED` where applicable;
- replacement/supersession transaction is complete when the artifact was previously Current;
- canonical replacement path physically exists and passes parser/hash/schema validation;
- deletion is recorded in a cleanup ledger with reason, evidence, replacement UID/hash when applicable, and post-delete residual scan.

If any proof is missing, deletion MUST be blocked with `CLEANUP_DELETE_NOT_PROVEN_SAFE`.

Protected Current Artifact paths MUST be registered before cleanup. Cleanup code MUST load that registry first and MUST_NOT maintain a private allow/deny list as a second authority.


A delete transaction MUST_NOT be considered complete at pre-delete authorization. After physical deletion, the cleanup ledger MUST enter the terminal chain `PRE_DELETE_AUTHORIZED -> DELETE_EXECUTED -> POST_DELETE_RESIDUAL_SCAN_PASS -> CLOSED`. Any `FAIL`, `PENDING`, missing post-delete evidence, surviving target, or recomputed residual reference MUST block Pre-formal and Release closure.

<!-- SECTION_UID: WEB-GOV-03-S056 -->
## 56. Universal Index / Continuity Transaction

Every construction stage MUST use the same Root Manifest → Registry/Index → Exact Artifact → Dependency Closure loading model. Whole-package rescans are allowed only for explicit integrity/audit operations.

Creating, replacing, moving, renaming, or deleting a Current artifact MUST atomically update forward dependency, reverse dependency, canonical path/name registry, current-owner index, supersession/cleanup ledger, and affected review/audit state.

Cross-layer, cross-stage, cross-page, Page/Visual reference, shared-owner port, provider/async, and data/runtime dependencies MUST remain bidirectionally resolvable. A broken producer/consumer edge or stale producer hash MUST block closure and mark affected consumers `REVERIFY_REQUIRED`.

<!-- SECTION_UID: WEB-GOV-03-S057 -->
## 57. Typed UID Resolution / Read-Write Target Lock

UID resolution MUST be typed and access-controlled. A normative Section UID (`WEB-GOV-*`) is a READ_ONLY governance reference and MUST_NOT be accepted as a construction write target. Governance registry UIDs are protected governance objects and MAY be mutated only in an explicit governance-maintenance mode that passes the Protected Current Artifact Delete/Mutation Gate.

Before any write, the executor MUST resolve the target Program Artifact UID and prove exact match of Work Unit UID, page/scope UID, owner UID, Construction Profile, canonical path, canonical filename, expected current hash, and producer Stage. A path that is valid for another registered artifact is still an invalid target for the current Work Unit.

Normative resolution MUST use Section UID -> Section Registry -> exact document path -> exact Section UID anchor -> current document hash. Free-text heading lookup, filename guessing, nearest-title fallback, fuzzy matching, or cross-document substitution is forbidden.


For every normative Section UID, the exact anchor MUST occur exactly once, the registered exact heading MUST occur exactly once, and the anchor MUST be immediately adjacent to that heading. The Section Registry binding digest MUST match `Section UID + Document ID + canonical path + exact heading`; a legal UID moved to another legal heading is an invalid resolution and MUST be blocked.

All program-construction identities and runtime references MUST resolve through the Current Typed Program Identity Authority. Program Artifact UID, Work Unit UID, page/scope UID, Owner UID, dependency/reverse-dependency refs, input artifact refs, and required test refs MUST each resolve exactly once to the expected identity type and CURRENT/PLANNED status. Co-signed Artifact/Manifest values do not prove identity existence.

The executor MUST persist a resolution receipt for every normative Section UID actually consumed. A resolved reference outside the declared effective normative set MUST_NOT influence execution; additional normative requirements must first be registered into the applicable manifest/index and the governance load receipt regenerated.

<!-- SECTION_UID: WEB-GOV-03-S058 -->
## 58. Universal Closure Evidence Continuity / Ledger Synchronization / Terminal CI Receipt

This invariant applies to `STAGE-01` through `STAGE-11`, including Stage-1 sub-phases such as Page Base Blueprint, Visual Base Blueprint, and Blueprint Binding. It also applies to Stage-02 functional contracts, Stage-03 visual design, Foundation Freeze, Implementation, Verification/QA, Release Candidate, Staging, Production Cutover, Production Acceptance, and Closure Operations.

A legal successor MUST NOT erase, revert, or silently rewrite already-proven predecessor facts. Closure mutation semantics are `MERGE_APPEND_OR_EXPLICIT_SUPERSEDE`, never destructive re-generation of a smaller Current ledger. Once a predecessor fact is proven true for the active lineage, `started`, `completed`, immutable source/checkpoint identity, gate result, replay proof, content-audit proof, and required run/evidence identity MUST remain resolvable in Current evidence until an explicit supersession/reverification transaction replaces it.

For every affected closure, the Current execution/evidence ledgers MUST be synchronized as one logical transaction. At minimum this covers `EXECUTION_STATE`, `RUN_MANIFEST`, `ARTIFACT_PLAN`, `GOVERNANCE_CURRENT`, branch baseline/current baseline, stage lock, sealed test baseline, stage evidence, dependency/reverse-dependency indexes, and the applicable closure receipt. A material mismatch in current phase, artifact count, authoritative hash, unresolved Authority count/identity, gate status, next legal transition, or predecessor proof MUST block closure with `CURRENT_LEDGER_SYNCHRONIZATION_DRIFT`.

A closure MUST preserve monotonic predecessor truth. The following are blocking defects unless explicit supersession evidence exists: `completed=true` while the corresponding start proof is absent; a previously required replay/content-audit proof disappears; a predecessor run/checkpoint/hash becomes unresolvable; a legal successor causes predecessor PASS to become FAIL solely because the successor exists; or a closure summary replaces a richer Current ledger while dropping required predecessor facts.

Materialization evidence and terminal closure CI receipt are separate identities. Materialization evidence binds the candidate bytes and the run that first proves the materialized artifacts. Terminal closure receipt binds the final validated head externally with at least `provider`, `repository_or_project`, `head_sha`, `run_id`, `job_denominator`, and `conclusion`. The terminal receipt is an external immutable receipt and MUST NOT be required to self-write its own `run_id` into the same commit it validates; doing so would create an infinite self-reference loop. A later ledger MAY reference that external receipt, but creating that later reference produces a new candidate head and therefore MUST NOT redefine the prior receipt as if it validated the new head.

Every Stage close MUST enforce this invariant through the common governance bundle. Stage-specific validators MAY add stricter fields but MUST NOT weaken continuity, synchronization, or terminal-receipt semantics. Missing predecessor evidence, destructive closure rewrite, self-referential terminal receipt, or cross-ledger drift MUST fail closed.

Required Evidence is not valid merely because a file/path exists. Before an evidence item may be marked `MATERIALIZED`, `PASS`, `CLOSED`, or used to satisfy a Stage exit gate, the exact bytes MUST pass the registered parser and the applicable schema/required-field validator. Malformed YAML/JSON, unparseable evidence, missing required fields, or a validator exception MUST block closure. Presence-only acceptance is forbidden.

Unresolved Authority identity continuity is exact, not denominator-only. Every carry-forward record MUST preserve the canonical tuple `gap_uid`, `authority_ref`, `disposition`, and `authority_evidence_ref` exactly against the current `SOURCE_DEPENDENCY_MAP` or an explicit authoritative successor ledger. Matching only the unresolved count or GAP UID is insufficient and MUST fail closed. A tuple change requires explicit authoritative supersession/resolution evidence; AI inference, alias substitution, default filling, or evidence-ref drift MUST NOT be accepted as continuity.

Every ledger-local terminal CI receipt projection that claims terminal receipt status MUST expose the canonical six fields `provider`, `repository_or_project`, `head_sha`, `run_id`, `job_denominator`, and `conclusion`, with identical values for the same receipt identity. Abbreviations such as `jobs` or `result` MAY exist only as non-authoritative display aliases and MUST NOT substitute for canonical fields. A receipt missing any canonical field, or two ledgers projecting different values for the same receipt, MUST block closure.

<!-- SECTION_UID: WEB-GOV-03-S059 -->
## 59. Stage Test Defect Feedback / Specification Evolution Closed Loop

Every lifecycle Stage test MUST record every reproduced bug, gap, validator defect, evidence defect, implementation deviation, and unresolved contract discovered during execution. A test run MUST_NOT close merely because its planned assertions finished; discovered defects and gaps require a durable defect/gap record with evidence, affected scope, current disposition, and whether they block Stage exit.

After each Stage test, the executor MUST compare the tested construction/production content against the Current governance specification and record any nonconformance. The required closed-loop order is:

`STAGE_TEST_EXECUTION -> DEFECT_GAP_RECORD -> PRODUCTION_CONFORMANCE_REVIEW -> DEFECT_SCOPE_CLASSIFICATION -> SPEC_PATCH_CANDIDATE -> MULTIDIRECTION_HIGH_PRESSURE_TEST -> VERSION_PROMOTION_V2_1_X -> SOURCE_CONTROL_VERSIONED_CANDIDATE_SYNC -> PREDECESSOR_BACKTRACE_REGRESSION -> FULL_CURRENT_RULE_REVALIDATION -> SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION -> FORMAL_FREEZE -> NEXT_STAGE_ELIGIBLE`

A defect scope MUST be classified before governance repair:

- `GLOBAL_SHARED`: the failure mode can recur across more than one Stage, profile, page, validator, ledger, or execution layer. The repair MUST be made at the common invariant layer and propagated to every affected normative mother specification, lifecycle contract, acceptance contract, validator, regression asset, versioning rule, and configured Source-Control Current governance authority. Patching only the Stage where the bug was first observed is forbidden.
- `STAGE_LOCAL`: the failure is proven to be unique to one Stage contract. The repair MUST remain Stage-scoped and MUST_NOT be generalized to other Stages without recurrence evidence or explicit higher-level Authority.

A governance candidate MUST pass multidirection/high-pressure tests before its `v2.1.X` version is promoted. Version promotion MUST be followed by predecessor backtrace regression and a full Current-rule revalidation. Any failure reopens the bugfix window and prohibits Formal Freeze. Only after the new version passes those checks may the configured Source-Control Current governance authority be promoted and the Stage become eligible for freeze and next-stage transition.

Every adopting system MUST configure exactly one Source-Control Single-Spec Authority adapter. The adapter MUST expose one canonical Current governance entry point, and every automated governance consumer MUST begin from that entry. The canonical path and provider identity are adapter-defined profile data and MUST_NOT become common governance semantics. Historical correction packages, predecessor versions, evidence files, local archives, branch-local copies, or stage-specific reports MUST_NOT act as competing Current specifications. A versioned candidate may be synchronized for evidence before backtrace, but it remains NONCURRENT until predecessor backtrace plus full revalidation pass and the adapter's single Current entry is atomically promoted.


<!-- SECTION_UID: WEB-GOV-03-S060 -->
## 60. Universal Business-Entity Completeness / Product-Neutral Execution Gate

The Business Entity completeness rules are common execution invariants, not product-specific requirements. Every adopting system MUST execute them using its own registered Product Profile, entity identities, routes, runtimes, and repositories without changing the common invariant semantics.

Stage execution MUST enforce the following responsibility split: Stage-01 extracts candidate Business Entities and parent/child/category relationships from Source Authority; Stage-02 materializes the authoritative Entity Inventory, Operation Matrix, Hierarchy Matrix, functional contracts, state dependencies, and unresolved Authority gaps; Stage-03 binds every required operation to an approved interaction/visual entry; Stage-04 freezes the entity/operation/hierarchy/UI acceptance denominator; Stage-05 implements the frozen denominator without invention or omission; Stage-06 runs executable end-to-end lifecycle tests for every required operation; Stage-10 repeats applicable effectful lifecycle acceptance against Production or the target release environment.

Stage-02 MUST remain BLOCKED while any required Business Entity is missing, any required operation is unclassified, any `NOT_APPLICABLE` lacks Authority evidence, any parent/child edge is unresolved, any required operation lacks a complete functional contract, or any business capability is represented only by a list/control/action count. Stage-03 MUST remain BLOCKED while a required operation lacks a visual/system interaction binding. Stage-05 MUST remain BLOCKED when implementation invents a contract not frozen upstream.

Product-specific evidence first observed in one system MAY justify a common-rule defect only after defect scope classification proves the defect class can recur outside that system. Product-specific examples and repositories remain empirical provenance; they MUST_NOT become common execution prerequisites.

Before recursive functional completion may execute, the candidate addition MUST pass function admission and minimal-closure controls. A score alone is never execution Authority. Automatic execution is allowed only when the source gap/REQUIRED operation is registered, the dependency is uniquely necessary, no equivalent capability already satisfies the requirement, no unresolved Authority ambiguity exists, and the addition remains inside the frozen dependency closure. Any out-of-closure dependency discovery MUST terminate the automatic chain and reopen design.

Execution MUST detect recursive dependency cycles and unauthorized denominator growth. Each expansion step MUST retain source gap UID, source Entity UID, REQUIRED operation, dependency edge, Authority reference, necessity score, minimal-necessity explanation, and visual-impact reference. Once all seed REQUIRED gaps are closed and no unresolved REQUIRED edges remain inside the frozen closure, further automatic expansion is forbidden.

Logic and visual state MUST advance together for user-visible or user-observable operations. Stage-03 must approve the visual binding before Stage-05 implementation; Stage-05 must not invent new visual patterns; Stage-06 and Stage-10 must verify the same operation across logic, state, control/trigger, pending/disabled state, success/error/recovery feedback, and visual projection.

Indexed validation MUST be used as a performance optimization without changing the validation denominator. The impact index and reverse-dependency index may select and cache unchanged inputs, but cannot suppress any validator affected by changed bytes, changed Section UIDs, changed semantic authority, or changed dependency closure. A full sweep before freeze MUST compare indexed results with the full package; divergence is blocking.


<!-- SECTION_UID: WEB-GOV-03-S061 -->
## 61. Interaction Topology / Workbench Continuity Execution Control

Stage execution MUST preserve one authoritative interaction topology from functional contract through visual design, implementation, QA, production acceptance, and later revision. Stage-02 owns functional-cluster boundaries, operation order, context/state continuity, allowed separation, cross-surface handoff, and conditional AI-interaction identity rules. Stage-03 owns the visual projection of that frozen topology, including grouping, adjacency, same-surface placement, support-panel separation, responsive reflow, and geometry. Stage-03 MUST NOT silently redefine Stage-02 functional topology.

Stage-02 MUST BLOCK when a continuous functional journey lacks a `FUNCTIONAL_WORKBENCH_CONTRACT` or `INTERACTION_TOPOLOGY_MATRIX`, when the workbench class is unresolved, or when required shared-context identity/transition semantics are missing. For declared AI-assisted interaction scopes, Stage-02 MUST also BLOCK when conversation identity transitions, multi-agent context equivalence, AI-output formalization boundary, revision lineage, or branch isolation/adoption are unresolved.

Stage-03 MUST BLOCK visual approval when required operations are present but visually fragmented contrary to the workbench contract; when an unrelated surface interrupts an atomic workbench; when required adjacency/order is broken; when a same-surface cluster is split without Authority; when a cross-surface transition lacks visible/interaction handoff; or when responsive reflow changes the approved semantic order.

Stage-05 MUST implement the frozen topology without invention or omission. Discovery that a required function cannot fit the approved topology, or that a new surface/context transition is needed, MUST reopen the appropriate Stage-02/03 contract rather than being solved ad hoc in implementation. Stage-06 and Stage-10 MUST execute topology-aware acceptance that proves not only presence of controls and runtime effects but continuity of the actual journey, shared context, transition/handoff behavior, revision lineage, branch isolation, and AI decision boundary when applicable.
