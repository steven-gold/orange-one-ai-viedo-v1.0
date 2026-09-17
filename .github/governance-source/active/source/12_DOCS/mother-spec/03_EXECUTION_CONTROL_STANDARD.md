---
document_id: WEB-GOV-03
version: 2.2.3
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
## 46. Governance Specification Development / Validation Lock Discipline

A released governance revision is immutable. A successor candidate MAY change reusable policy only under an explicit, pre-existing exact-scope authorization and MUST preserve predecessor history.

Every formal validation cycle MUST freeze the candidate governance UID/hash and immutable input baseline before execution. Normative mutation during that validation cycle invalidates its acceptance result. Test fixtures carry observable facts only; expected outcomes belong to the external harness and MUST_NOT instruct validators what conclusion to return.

Reproduced defects MUST be recorded, classified by owning layer, repaired in a successor candidate or non-policy owning layer as applicable, and freshly revalidated. Product-specific evidence MAY be test input but MUST_NOT become a common-policy dependency.

<!-- SECTION_UID: WEB-GOV-03-S051 -->
## 51. Validation-Cycle Retry / Relock Execution Control

When a locked policy revision later exposes a reproduced defect, the locked revision remains immutable. A successor candidate MUST be created under explicit authorization; unrelated changes MUST NOT be carried into the defect scope.

Fresh retry/replay MUST begin from registered immutable inputs plus authorized owning-layer remediation, with prior generated outputs and stale test residue removed. The retry MUST bind immutable input hashes, candidate governance UID/hash, evidence-cycle identity, output root, and clean-start evidence.

If candidate normative bytes change after the retry begins, that retry is invalid for closure and MUST restart under the new candidate identity. Prior-result reuse, fixture patching to manufacture PASS, and stale-output carry-forward are forbidden.

<!-- SECTION_UID: WEB-GOV-03-S052 -->
## 52. Source Enumeration Before Classification / Dual-Blueprint Dependency Order

Source intake MUST close Raw Source Capture before Source Structure Enumeration; enumeration MUST close before segment mapping; source facts MUST materialize before responsibility classification; Page and Visual Base Blueprint compilation MUST remain separate; binding occurs only after both current blueprint hashes exist.

Validators MUST distinguish predecessor closure facts from legal successor activity. Starting a registered legal successor MUST NOT retroactively invalidate an otherwise valid predecessor merely because the global execution state has advanced. Illegal skip, proof loss, Authority identity drift, or unregistered successor remains fail-closed.

Semantic granularity is responsibility-based rather than syntax-based. Every candidate terminal unit MUST be homogeneous across Owner, Lifecycle, Approval, Version, Acceptance Scope, Planning Domain, Release/Rollback Identity, Applicability, and Closure Identity, or carry explicit `MIXED_ALLOWED` evidence. Every applicable work unit MUST re-run this check for its own terminal units.

<!-- SECTION_UID: WEB-GOV-03-S053 -->
## 53. Universal Supersession / Cleanup Transaction

Supersession is a transaction, not a metadata label. The rule applies to every Current artifact class, not only Source Intake.

The mandatory order is:

`REGISTER_REPLACEMENT -> RESOLVE_FORWARD_REFERENCES -> RESOLVE_REVERSE_DEPENDENCIES -> MARK_IMPACTED_CONSUMERS_REVERIFY_REQUIRED -> PROVE_ZERO_CURRENT_REFERENCE_TO_SUPERSEDED_OWNER -> REMOVE_SUPERSEDED_FROM_CURRENT_INDEX -> DELETE_GENERATED_DUPLICATE/TEMP/BACKUP/OBSOLETE_ARTIFACTS -> UPDATE INDEXES -> UPDATE CLEANUP_LEDGER -> ORPHAN/RESIDUAL/BROKEN_REFERENCE_SCAN`

Raw Source MAY remain as immutable historical/reference evidence, but MUST_NOT remain a Current Owner after supersession.

A stage cannot close while any of the following is non-zero: Current reference to superseded owner, duplicate Current owner, orphan required artifact, unjustified residual file, broken reference.

<!-- SECTION_UID: WEB-GOV-03-S054 -->
## 54. Index / Hash / Lazy-Load Execution Rule

Every governed execution cycle MUST use index-first loading. A Work Unit resolves its registered manifest, then exact artifact refs, then dependency closure. Re-reading the full governance package or all page construction files for an ordinary local change is forbidden.

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

Every governed construction work unit MUST use the same Root Manifest → Registry/Index → Exact Artifact → Dependency Closure loading model. Whole-package rescans are allowed only for explicit integrity/audit operations.

Creating, replacing, moving, renaming, or deleting a Current artifact MUST atomically update forward dependency, reverse dependency, canonical path/name registry, current-owner index, supersession/cleanup ledger, and affected review/audit state.

Cross-layer, cross-work-unit, cross-page, Page/Visual reference, shared-owner port, provider/async, and data/runtime dependencies MUST remain bidirectionally resolvable. A broken producer/consumer edge or stale producer hash MUST block closure and mark affected consumers `REVERIFY_REQUIRED`.

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

Closure continuity applies to every governed work unit and selected execution-profile step. A legal successor MUST NOT erase, revert, or silently rewrite proven predecessor facts. Closure mutation semantics are `MERGE_APPEND_OR_EXPLICIT_SUPERSEDE`.

Current execution/evidence ledgers MUST synchronize as one logical transaction for the affected scope, including immutable baseline identity, governance UID, work-unit/profile-step identity when applicable, artifact/evidence plans, dependency indexes, unresolved Authority identity, gate state, and next legal transition. Material drift MUST block closure.

Materialization evidence and terminal CI receipt are separate identities. Terminal receipt MUST externally bind provider, repository/project, head SHA, evidence-cycle identity, job denominator, and conclusion without requiring self-writing into the same commit. Required evidence must parse and pass its schema/field validator; presence alone is not evidence validity.

Unresolved Authority continuity is exact, not count-only. AI inference, alias substitution, default filling, or evidence-reference drift MUST_NOT resolve external Authority.

<!-- SECTION_UID: WEB-GOV-03-S059 -->
## 59. Validation Feedback / Specification Evolution Closed Loop

Every governed validation cycle MUST durably record reproduced bugs, gaps, validator/harness defects, evidence defects, implementation deviations, unresolved contracts, and suspected reusable policy deficiencies. Finishing planned assertions alone is not closure.

Each issue MUST be classified by one primary owner: reusable policy, validation/harness implementation, product/contract materialization, runtime/implementation, non-normative evidence/state, or external/shared Authority. Product-specific evidence becomes a common-policy candidate only when recurrence/generalizability is proven.

Reusable-policy candidates remain non-normative until explicit authorization, atomic successor promotion, multidirectional regression, active-consumer projection verification, and full Current-policy revalidation pass. A provider/project adapter MUST expose exactly one Current governance entry; historical candidates and evidence MUST remain non-current.

<!-- SECTION_UID: WEB-GOV-03-S060 -->
## 60. Universal Business-Entity Completeness / Product-Neutral Execution Gate

Business Entity completeness is a common semantic invariant. Source-intake capability extracts entity/relationship candidates; functional-contract capability materializes entity inventory, operation/hierarchy matrices, functional contracts, state dependencies, and unresolved Authority gaps; visual-design capability binds applicable operations to approved interaction/visual entries; freeze capability locks the accepted denominator; implementation consumes it without invention; verification and Production acceptance execute applicable lifecycle behavior.

Required entity/operation/hierarchy/functional/visual continuity gaps MUST block the capability that owns them. Automatic functional completion is allowed only for a uniquely necessary minimal closure inside authorized dependency bounds; two or more materially distinct viable behaviors constitute an Authority gap and MUST block AI autofill.

Logic and visual state MUST remain synchronized for user-visible or observable operations. Indexed validation MAY optimize performance but MUST NOT change the semantic denominator or suppress an impacted validator.

<!-- SECTION_UID: WEB-GOV-03-S061 -->
## 61. Interaction Topology / Workbench Continuity Execution Control

Governed execution MUST preserve one authoritative interaction topology from functional contract through approved visual projection, implementation, verification, Production acceptance, and later revision.

Functional-contract Authority owns workbench boundaries, operation order, context/state continuity, allowed separation, cross-surface handoff, and conditional AI-interaction identity. Visual Design Authority owns approved projection and geometry but MUST NOT silently redefine functional topology. Implementation MUST consume both without invention or omission.

Verification/Production acceptance MUST prove actual journey continuity, context handoff, revision lineage, branch isolation/adoption, and AI decision boundary when applicable. Discovery of a required topology change MUST reopen the owning contract/design Authority rather than be solved ad hoc downstream.

<!-- SECTION_UID: WEB-GOV-03-S062 -->
## 62. Canonical Execution Engine / Checkpoint Control / Clean-Restart Rule

Every governed execution cycle MUST use one canonical engine contract: `Global Preflight -> Frozen Canonical Manifests -> Dependency-Ordered Batch Execution -> Local Impact Validation -> Checkpoint Reconciliation -> Final Fresh Full Sweep`.

Selected execution profiles MAY specialize operations and artifact schemas, but MUST consume the same common required-field, applicability, classification, effective-overlay, denominator, Authority, and evidence rules. Profile-local copies MUST_NOT diverge from common policy.

Before remediation, the engine MUST validate `EXECUTION_CYCLE_PREFLIGHT_RECEIPT`. After each batch it MUST update the affected reverse-dependency closure and append `RESOLUTION_LEDGER`; full sweeps are mandatory after shared/common-engine changes, registered category closure, before cycle closure, and before policy/release freeze.

Harness defects MUST NOT consume product blocker credit or create product Authority. Authorized normative promotion invalidates prior-cycle closure credit under the old UID; generated outputs/derived state are reset, immutable predecessor/external Authority is preserved at its owner, and fresh execution restarts under the new UID.

<!-- SECTION_UID: WEB-GOV-03-S063 -->
## 63. Mandatory Session Bootstrap / Resume Gate

Before any Current State judgment, planning, mutation, test, commit, workflow execution, deployment decision, closure claim, or continuation decision, the executor MUST complete one `SESSION_BOOTSTRAP_RESUME_GATE` in this exact dependency order:

1. Resolve the live repository, target branch, commit SHA, and tree SHA from the repository itself.
2. Resolve the formal Registry / Current Governance entry and immutable Current Governance UID; chat memory, historical summaries, Stage labels, profile labels, and run labels MUST_NOT select Current Governance.
3. Read the Current Mother Governance in canonical order `WEB-GOV-01 -> WEB-GOV-02 -> WEB-GOV-03 -> WEB-GOV-04` through the Current Section/Root registries.
4. Resolve Current Canonical Authority for the requested semantic concern.
5. Classify and lock the Current Primary Task Layer under WEB-GOV-03-S064.
6. Resolve the one legal Active Primary Work Unit for that task layer; if none exists, enter `WORK_UNIT_RESOLUTION_GATE` under WEB-GOV-03-S065 before doing effectful work.
7. Resolve Canonical Owner Mapping, exact write target, forward dependencies, reverse dependencies, and impacted consumers.
8. Resolve the persisted Current Resume Point and verify the last completed effectful action.
9. Resolve Current Audit / Evidence State and prove that evidence belongs to the Current Governance UID/revision or is explicitly classified historical/non-current evidence.
10. Resolve the selected Execution Profile only when applicable; profile-local Stage/step identity MUST remain subordinate to the Current Primary Task Layer and common Mother Policy.
11. Resolve Entry Conditions, Dependencies, Definition of Done, required Gates, terminal transition, and closure evidence requirements.
12. Recheck live commit/tree and Current Governance identity immediately before the first write or effectful action.

The gate MUST fail closed when any required Current identity, Authority, task layer, Work Unit, owner, Resume Point, evidence identity, dependency, reference, revision, or transition is missing, stale, ambiguous, conflicting, or points to a superseded/deleted owner.

`CHAT_MEMORY != CURRENT_TRUTH` and `INNER_STAGE_IDENTITY != PRIMARY_TASK_SELECTION` are permanent invariants.

<!-- SECTION_UID: WEB-GOV-03-S064 -->
## 64. Task Layer Classification / Primary Task Lock

Every governed request MUST be classified before Work Unit execution into exactly one Current Primary Task Layer:

- `GOVERNANCE_MAINTENANCE`
- `PRODUCT_STAGE_EXECUTION`
- `TEST_OR_VALIDATION_MAINTENANCE`
- `EVIDENCE_STATE_MAINTENANCE`
- `DEPLOYMENT_OR_PRODUCTION`

The classification MUST derive from the explicit user directive, Current Authority, authorized Change Request, Current Work Unit/Resume state, and applicable dependency/impact evidence. A Stage number, profile step, historical run, failing test, open blocker, or nearby executable MUST_NOT silently redefine the requested Primary Task Layer.

When `GOVERNANCE_MAINTENANCE` is primary, product Stage artifacts MAY be read only as evidence, regression provenance, dependency context, or impacted-consumer context unless a separately authorized product Work Unit becomes the legal primary task. Governance maintenance MUST_NOT drift into product materialization merely because a product Stage remains blocked.

Task-layer changes MUST be explicit, evidence-backed, recorded in Resume/Current State, and re-run the full Session Bootstrap / Resume Gate before effectful work continues.

<!-- SECTION_UID: WEB-GOV-03-S065 -->
## 65. Work Unit Resolution Gate

If the Current Primary Task Layer has no legal Active Primary Work Unit, execution MUST enter `WORK_UNIT_RESOLUTION_GATE`; absence of an Active Work Unit is not permission for AI to invent one or jump to the nearest Stage, file, test, or blocker.

The legal successor Work Unit MAY be resolved only from registered Current Authority, a valid explicit authorization or Change Request, Current impact set, dependency graph, applicability decision, unresolved blocker ledger, prior closure transition, and canonical owner mapping.

The resolution MUST prove:

- predecessor/current Work Unit state and terminal disposition;
- requested Primary Task Layer;
- candidate successor scope and canonical owner;
- dependency and reverse-dependency legality;
- applicability and Entry Conditions;
- no duplicate/parallel Work Unit or second owner;
- exact Resume Point and Definition of Done;
- whether the successor is blocked, executable, or requires human/Authority decision.

If two or more materially distinct successor Work Units remain legal without Authority selecting one, the result is `WORK_UNIT_RESOLUTION_AMBIGUOUS` and effectful execution MUST BLOCK. AI MUST_NOT create a synthetic Work Unit merely to continue activity.

<!-- SECTION_UID: WEB-GOV-03-S066 -->
## 66. Governance Maintenance Credit Isolation

Governance maintenance and product completion are different accounting domains. The following work MAY repair governance correctness but MUST receive zero product-stage gap-reduction and zero product-completion credit unless it separately materializes an already-authorized product requirement at the canonical product owner and passes that product requirement's own acceptance gates:

- Mother/Current governance repair or promotion;
- Registry, index, reference, checksum, source-identity, supersession, or residual cleanup;
- validator, scanner, classifier, parser, harness, workflow, CI, gate, or test-infrastructure repair;
- evidence, projector, Current State, Resume, ledger, report, or receipt repair;
- migration of stale/deleted/superseded governance references;
- negative-regression preservation or historical evidence cleanup.

`GOVERNANCE_MAINTENANCE_PASS != PRODUCT_STAGE_PASS`.

A governance Work Unit MUST record its own closure evidence and MUST_NOT decrement product blocker/gap denominators solely because the governance machinery became correct. Product denominators change only from fresh product/contract evidence under the legal product owner and Current Authority.

<!-- SECTION_UID: WEB-GOV-03-S067 -->
## 67. Terminal Closure Observation / Context Continuity Gate

A Work Unit, validation cycle, promotion, cleanup transaction, workflow-backed Gate, or release Gate MUST_NOT receive terminal closure credit from an inner step, job subset, generated preterminal projection, queued/in-progress workflow, timeout, cancellation, skipped terminal, or historical successful run.

When terminal execution is delegated to CI or another external executor, closure requires an observed outer terminal conclusion bound to the exact repository/project, commit SHA, evidence-cycle identity, required job/test denominator, and Current Governance UID. `INNER_STEP_PASS != TERMINAL_RUN_PASS`.

Before moving to a new Primary Task Layer or Work Unit, the executor MUST persist the terminal disposition, exact evidence refs, unresolved blockers, Current Resume Point, and legal next transition. A later session MUST recover from those persisted facts through WEB-GOV-03-S063 rather than from conversational memory.

<!-- SECTION_UID: WEB-GOV-03-S068 -->
## 68. Semantic Residual Classification / Disposition Gate

Before any Current artifact, validator, runner, workflow helper, generated projector, temporary file, backup, intermediate, superseded implementation, or other residual content may be kept, migrated, or deleted, the owning Work Unit MUST classify that residual by content and execution role. Filename age, naming pattern, file count, directory location, historical Stage number, or absence from a partial search MUST_NOT be treated as deletion proof.

Every residual classification MUST evaluate all six dimensions:

1. CANONICAL_OWNER
2. FORWARD_REFERENCE
3. REVERSE_REFERENCE
4. RUNTIME_OR_WORKFLOW_REACHABILITY
5. TEST_REGRESSION_ROLE
6. HISTORICAL_RETENTION_ROLE

The legal disposition vocabulary is closed:

- CURRENT_REQUIRED -> KEEP_ACTIVE
- HISTORICAL_PROVENANCE -> KEEP_NON_CURRENT
- NEGATIVE_REGRESSION_PATTERN -> KEEP_AS_NON_CURRENT_TEST_OR_SIGNATURE
- SUPERSEDED_ACTIVE_CONTENT -> REMOVE_OR_MIGRATE
- DEAD_OR_UNREFERENCED_ACTIVE_CONTENT -> REMOVE
- TEMP_BACKUP_INTERMEDIATE -> REMOVE
- UNKNOWN -> BLOCK

UNKNOWN is fail-closed. AI MUST_NOT silently convert uncertainty into REMOVE, KEEP, SATISFIED, or product completion.

For executable/validator/runner cleanup, deletion additionally requires proof that the candidate is not an active direct or transitive workflow consumer, not a Current registry/projector/owner target, not required by Current Authority materialization, not the sole preserved negative-regression signature for a known defect, and not required historical provenance. A validator MAY remain even when its former producer is gone when it directly protects a Current invariant or negative-regression signature.

A removable cohort SHOULD be mutated atomically when the files share one proven disposition and dependency closure. The transaction MUST preserve required Authority machinery, Current owners, Current projectors, historical provenance, and required regression signatures; then run post-delete reference/residual scans and exact-head terminal validation under the applicable gates.

This section classifies residuals before WEB-GOV-03-S053 and WEB-GOV-03-S055 perform supersession/delete operations. It does not replace those owners.

Governance residual cleanup is governed by WEB-GOV-03-S066 and receives zero product-stage gap reduction or completion credit unless separate fresh product-owner evidence independently changes a product denominator.
