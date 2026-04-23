# LLM Connection and Config Persistence Bugfix Design

## Overview

This design addresses two critical bugs in the TaskTree intelligent reminder system:

1. **Bug #1: Provider Name Mismatch** - The LLMService constructor has a typo (`provider="minmax"` instead of `"minimax"`), causing API connectivity tests to fail with "Unknown provider: minimax" errors when the frontend sends the correct spelling.

2. **Bug #2: Analysis Config Persistence** - The frontend Settings component uses a separate `analysisConfig` state but the form loading/saving logic doesn't properly synchronize this state with the form values, causing analysis dimension toggles to not persist correctly after page refresh.

The fix will normalize provider name handling in the backend and properly integrate the analysis config state with the form in the frontend.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug
  - For Bug #1: When frontend sends `provider="minimax"` but backend expects exact match with typo `"minmax"`
  - For Bug #2: When analysis_config toggles are changed and saved but not properly restored on page load
- **Property (P)**: The desired behavior for buggy inputs
  - For Bug #1: Provider name matching should be case-insensitive or handle both "minimax" and "minmax"
  - For Bug #2: Analysis config toggles should persist and restore correctly
- **Preservation**: Existing functionality that must remain unchanged
  - Other LLM providers (openai, anthropic, custom) must continue working
  - Other settings fields must continue persisting correctly
  - Actual LLM API calls for task analysis must continue functioning
- **LLMService**: The service class in `backend/app/services/llm_service.py` that handles LLM provider routing
- **test_connection**: The API endpoint in `backend/app/api/v1/notification_settings.py` that validates LLM connectivity
- **Settings.tsx**: The frontend component in `frontend/src/pages/Settings/Settings.tsx` that manages user settings
- **analysisConfig**: The React state variable that holds analysis dimension toggle states (overdue, progress_stalled, etc.)
- **UserNotificationSettings**: The database model that stores user notification configuration including `analysis_config` JSON field

## Bug Details

### Bug #1: Provider Name Mismatch

#### Bug Condition

The bug manifests when a user attempts to test their LLM connection with the "minimax" provider. The `LLMService.__init__` method has a default parameter typo (`provider: str = "minmax"`), and the `_call_api` method performs case-sensitive string comparison. When the frontend sends `provider="minimax"` (correct spelling), the backend fails to match it in the provider routing logic.

**Formal Specification:**
```
FUNCTION isBugCondition_ProviderMismatch(input)
  INPUT: input of type TestConnectionRequest
  OUTPUT: boolean
  
  RETURN input.provider == "minimax"
         AND backend_llm_service_init_default == "minmax"
         AND provider_routing_logic_is_case_sensitive == true
         AND connection_test_fails_with_unknown_provider_error == true
END FUNCTION
```

#### Examples

- **Example 1**: User selects "Minimax" provider, enters valid API key and model, clicks "Test Connection" → Expected: Connection success with response time. Actual: "Unknown provider: minimax" error after timeout.
- **Example 2**: User saves settings with provider="minimax" → Expected: Settings saved and can be used for task analysis. Actual: Settings saved but subsequent API calls may fail with provider mismatch.
- **Example 3**: Backend creates LLMService with default parameters → Expected: Provider defaults to "minimax". Actual: Provider defaults to "minmax" (typo).
- **Edge Case**: User selects "OpenAI" or "Anthropic" provider → Expected: Works correctly. Actual: Works correctly (no bug for other providers).

### Bug #2: Analysis Config Persistence

#### Bug Condition

The bug manifests when a user toggles analysis dimension switches (overdue, progress_stalled, dependency_unblocked, team_load, risk_prediction) and saves settings. The Settings component maintains a separate `analysisConfig` state object, but the form loading logic doesn't properly restore this state from the API response, and the form saving logic doesn't properly include it in the submission.

**Formal Specification:**
```
FUNCTION isBugCondition_ConfigPersistence(input)
  INPUT: input of type AnalysisConfigUpdate
  OUTPUT: boolean
  
  RETURN input.analysis_config IS NOT NULL
         AND user_toggles_analysis_dimensions == true
         AND user_saves_settings == true
         AND page_refreshes == true
         AND loaded_analysis_config != saved_analysis_config
END FUNCTION
```

#### Examples

- **Example 1**: User disables "overdue" toggle, saves settings, refreshes page → Expected: "overdue" toggle remains disabled. Actual: "overdue" toggle resets to enabled (default).
- **Example 2**: User enables all analysis dimensions, saves, refreshes → Expected: All toggles remain enabled. Actual: Toggles may reset to default values.
- **Example 3**: User changes multiple toggles, saves without refresh → Expected: Changes reflected in current session. Actual: May work in current session but lost on refresh.
- **Edge Case**: User changes other settings (webhook, API key) without touching analysis config → Expected: Other settings persist correctly. Actual: Works correctly (no bug for other fields).

## Expected Behavior

### Bug #1: Provider Name Matching Should Be Robust

**Correct Behavior:**
When a user tests their LLM connection with provider="minimax", the system should successfully route to the `_call_minimax` method and return connection results. The provider matching logic should handle both "minimax" and "minmax" spellings, or normalize to a single canonical form.

### Bug #2: Analysis Config Should Persist Correctly

**Correct Behavior:**
When a user toggles analysis dimension switches and saves settings, the system should:
1. Include the `analysisConfig` state in the form submission payload
2. Save the analysis_config JSON to the database
3. On page load, fetch the saved analysis_config and restore both the `analysisConfig` state and any form-related values
4. Maintain synchronization between the `analysisConfig` state and the saved database values

### Preservation Requirements

**Unchanged Behaviors:**
- Other LLM providers (openai, anthropic, custom) must continue to work exactly as before
- Other notification settings fields (dingtalk_webhook, dingtalk_secret, llm_api_key, llm_model, llm_group_id, daily_limit, enabled) must continue to persist correctly
- Actual LLM API calls for task analysis (analyze_tasks, analyze_task_complexity, etc.) must continue functioning with the corrected provider logic
- Other tabs in the Settings page (profile, password, about) must continue to function normally
- Backend encryption/decryption of API keys must continue working
- Frontend form validation and UI interactions must remain unchanged

**Scope:**
All inputs that do NOT involve:
- Testing connection with provider="minimax"
- Saving/loading analysis_config toggles

should be completely unaffected by this fix. This includes:
- Mouse clicks and interactions with other form fields
- Saving settings without changing analysis dimensions
- Using other LLM providers
- All other API endpoints and services

## Hypothesized Root Cause

Based on the bug description and code analysis, the most likely issues are:

### Bug #1: Provider Name Mismatch

1. **Typo in Default Parameter**: The `LLMService.__init__` method has `provider: str = "minmax"` instead of `provider: str = "minimax"`, creating inconsistency with the frontend's expected value.

2. **Case-Sensitive String Comparison**: The `_call_api` method uses exact string matching:
   ```python
   p = self.provider.lower()
   if p in ("minimax", "minmax"):  # Currently only checks lowercase
   ```
   When the frontend sends "minimax", it should match, but the logic may not handle all variations consistently.

3. **Frontend-Backend Contract Mismatch**: The frontend `LLM_PROVIDERS` object uses "minimax" as the key, but the backend default uses "minmax", creating a mismatch in the expected provider identifier.

### Bug #2: Analysis Config Persistence

1. **State-Form Desynchronization**: The Settings component maintains `analysisConfig` as a separate state variable, but the form loading logic doesn't properly update this state when settings are fetched from the API.

2. **Form Submission Missing State**: The `handleSaveReminder` function includes `analysisConfig` in the submission, but the form's `onFinish` handler receives `values` from the form, which doesn't include the separate state.

3. **Initial Load Timing**: The `useEffect` that loads settings may not properly synchronize the `analysisConfig` state with the form values, causing the toggles to show default values instead of saved values.

## Correctness Properties

Property 1: Bug Condition - Provider Name Matching

_For any_ test connection request where the provider is "minimax" (or case variations) and valid credentials are provided, the fixed LLMService SHALL successfully route to the appropriate provider method (_call_minimax, _call_openai, or _call_anthropic) and return connection results without "Unknown provider" errors.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Bug Condition - Analysis Config Persistence

_For any_ settings update where analysis_config contains toggle states (overdue, progress_stalled, dependency_unblocked, team_load, risk_prediction), the fixed system SHALL persist these values to the database and correctly restore them on subsequent page loads, maintaining the user's selected configuration.

**Validates: Requirements 2.4, 2.5**

Property 3: Preservation - Other Providers

_For any_ test connection request where the provider is NOT "minimax" (e.g., "openai", "anthropic", "custom"), the fixed LLMService SHALL produce exactly the same behavior as the original code, preserving all existing functionality for other providers.

**Validates: Requirements 3.1**

Property 4: Preservation - Other Settings Fields

_For any_ settings update that does NOT involve analysis_config toggles (e.g., updating dingtalk_webhook, llm_api_key, daily_limit), the fixed system SHALL produce exactly the same behavior as the original code, preserving all existing persistence logic for other fields.

**Validates: Requirements 3.2, 3.5**

Property 5: Preservation - LLM API Calls

_For any_ LLM service method call (analyze_tasks, analyze_task_complexity, generate_task_suggestions, etc.) that uses the corrected provider matching logic, the fixed system SHALL produce the same functional results as the original code, preserving all existing LLM analysis capabilities.

**Validates: Requirements 3.3**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

#### Bug #1: Provider Name Mismatch

**File**: `backend/app/services/llm_service.py`

**Function**: `LLMService.__init__` and `_call_api`

**Specific Changes**:

1. **Fix Default Parameter Typo**: Change the default parameter in `__init__` from `provider: str = "minmax"` to `provider: str = "minimax"` to match the frontend's expected value.

2. **Normalize Provider Name Handling**: In the `_call_api` method, ensure the provider matching logic handles both "minimax" and "minmax" consistently:
   ```python
   p = self.provider.lower()
   # Accept both "minimax" and "minmax" for backward compatibility
   if p in ("minimax", "minmax"):
       return await self._call_minimax(prompt)
   ```

3. **Update PROVIDERS Dictionary**: Ensure the `PROVIDERS` class variable uses "minimax" as the canonical key to match the frontend.

#### Bug #2: Analysis Config Persistence

**File**: `frontend/src/pages/Settings/Settings.tsx`

**Component**: `Settings`

**Specific Changes**:

1. **Synchronize State on Load**: In the `useEffect` that loads reminder settings, ensure the `analysisConfig` state is properly updated from the API response:
   ```typescript
   const ac = res.data.analysis_config || {};
   setAnalysisConfig({
     overdue: ac.overdue ?? true,
     progress_stalled: ac.progress_stalled ?? true,
     dependency_unblocked: ac.dependency_unblocked ?? true,
     team_load: ac.team_load ?? true,
     risk_prediction: ac.risk_prediction ?? true,
   });
   ```
   This code already exists, so verify it's working correctly.

2. **Ensure Form Submission Includes State**: In the `handleSaveReminder` function, verify that `analysisConfig` is included in the API call:
   ```typescript
   const res = await reminderSettingsAPI.updateSettings({
     // ... other fields
     analysis_config: analysisConfig,  // Already present
   });
   ```
   This code already exists, so verify it's working correctly.

3. **Verify Backend Persistence**: Ensure the backend `create_or_update_settings` endpoint properly handles the `analysis_config` field:
   ```python
   if settings_data.analysis_config is not None:
       settings.analysis_config = json.dumps(settings_data.analysis_config, ensure_ascii=False)
   ```
   This code already exists in `backend/app/api/v1/notification_settings.py`.

**Note**: After reviewing the code, Bug #2 appears to be correctly implemented in the current codebase. The issue may be a transient bug or user error. However, we should add defensive checks and logging to ensure robustness.

4. **Add Defensive Null Checks**: Ensure the frontend handles cases where `analysis_config` is null or undefined in the API response.

5. **Add Backend Validation**: Ensure the backend validates that `analysis_config` is a valid JSON object before saving.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

#### Bug #1: Provider Name Mismatch

**Test Plan**: Write tests that call `LLMService` with `provider="minimax"` and verify the provider routing logic. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Default Parameter Test**: Create `LLMService()` with no parameters and verify `self.provider` equals "minmax" (will show the typo on unfixed code)
2. **Minimax Provider Test**: Create `LLMService(provider="minimax")` and call `test_connection()` (will fail with "Unknown provider" on unfixed code)
3. **Case Variation Test**: Create `LLMService(provider="Minimax")` and verify routing (may fail on unfixed code)
4. **API Endpoint Test**: Call `/notifications/test-connection` with `provider="minimax"` via HTTP (will fail on unfixed code)

**Expected Counterexamples**:
- `LLMService()` creates instance with `provider="minmax"` (typo)
- `test_connection()` with `provider="minimax"` raises "Unknown provider: minimax" exception
- Possible causes: typo in default parameter, case-sensitive string matching, missing normalization

#### Bug #2: Analysis Config Persistence

**Test Plan**: Write tests that save analysis_config via the API, then fetch it back and verify the values match. Simulate page refresh by clearing component state and reloading. Run these tests on the UNFIXED code to observe failures.

**Test Cases**:
1. **Save and Load Test**: Set all toggles to false, save, reload settings, verify all are false (may fail on unfixed code)
2. **Partial Update Test**: Change only one toggle, save, reload, verify only that toggle changed (may fail on unfixed code)
3. **Null Config Test**: Save settings without analysis_config, reload, verify defaults are applied (should work on unfixed code)
4. **Frontend State Test**: Toggle switches in UI, save, clear state, reload, verify switches reflect saved values (may fail on unfixed code)

**Expected Counterexamples**:
- Analysis config toggles reset to default values after page refresh
- Saved analysis_config in database doesn't match loaded values in frontend
- Possible causes: state-form desynchronization, missing state in form submission, timing issues in useEffect

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed functions produce the expected behavior.

#### Bug #1: Provider Name Matching

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition_ProviderMismatch(input) DO
  llm_service := LLMService(provider=input.provider, api_key=input.api_key, model=input.model)
  result := llm_service.test_connection()
  ASSERT result.success == true
  ASSERT "Unknown provider" NOT IN result.error
END FOR
```

**Test Cases**:
- Input: `provider="minimax"`, valid credentials → Assert: connection succeeds
- Input: `provider="Minimax"` (capitalized) → Assert: connection succeeds
- Input: `provider="minmax"` (typo) → Assert: connection succeeds (backward compatibility)

#### Bug #2: Analysis Config Persistence

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition_ConfigPersistence(input) DO
  save_result := save_settings(input.analysis_config)
  ASSERT save_result.success == true
  
  loaded_result := load_settings()
  ASSERT loaded_result.analysis_config == input.analysis_config
END FOR
```

**Test Cases**:
- Input: All toggles false → Assert: loaded config has all toggles false
- Input: Mixed toggle states → Assert: loaded config matches saved states exactly
- Input: All toggles true → Assert: loaded config has all toggles true

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed functions produce the same result as the original functions.

#### Preservation for Other Providers

**Pseudocode:**
```
FOR ALL input WHERE input.provider NOT IN ("minimax", "minmax") DO
  result_original := LLMService_original(input).test_connection()
  result_fixed := LLMService_fixed(input).test_connection()
  ASSERT result_original == result_fixed
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for other providers (openai, anthropic, custom), then write property-based tests capturing that behavior.

**Test Cases**:
1. **OpenAI Provider Preservation**: Verify `provider="openai"` works identically before and after fix
2. **Anthropic Provider Preservation**: Verify `provider="anthropic"` works identically before and after fix
3. **Custom Provider Preservation**: Verify `provider="custom"` works identically before and after fix
4. **LLM Analysis Methods Preservation**: Verify `analyze_tasks`, `analyze_task_complexity`, etc. work identically before and after fix

#### Preservation for Other Settings

**Pseudocode:**
```
FOR ALL input WHERE input does NOT modify analysis_config DO
  result_original := save_settings_original(input)
  result_fixed := save_settings_fixed(input)
  ASSERT result_original == result_fixed
  
  loaded_original := load_settings_original()
  loaded_fixed := load_settings_fixed()
  ASSERT loaded_original == loaded_fixed
END FOR
```

**Test Plan**: Observe behavior on UNFIXED code first for other settings fields (webhook, API key, daily_limit), then write property-based tests capturing that behavior.

**Test Cases**:
1. **Webhook Persistence**: Verify dingtalk_webhook saves and loads correctly
2. **API Key Persistence**: Verify llm_api_key encrypts, saves, and decrypts correctly
3. **Daily Limit Persistence**: Verify daily_limit saves and loads correctly
4. **Enabled Flag Persistence**: Verify enabled flag saves and loads correctly

### Unit Tests

- Test `LLMService.__init__` with various provider names (minimax, Minimax, minmax, openai, anthropic)
- Test `_call_api` routing logic for all providers
- Test `test_connection` endpoint with valid and invalid credentials
- Test analysis_config serialization and deserialization in backend
- Test Settings component state management for analysis toggles
- Test form submission includes all required fields
- Test edge cases (null values, empty strings, missing fields)

### Property-Based Tests

- Generate random provider names and verify routing logic handles them gracefully
- Generate random analysis_config objects and verify persistence round-trip
- Generate random settings combinations and verify other fields are unaffected by the fix
- Test that all provider variations (case, spelling) produce consistent results

### Integration Tests

- Test full flow: user selects provider, enters credentials, tests connection, saves settings
- Test full flow: user toggles analysis dimensions, saves, refreshes page, verifies toggles persist
- Test that LLM analysis features work end-to-end with the fixed provider matching
- Test that other settings tabs (profile, password) continue working after the fix
