# Bugfix Requirements Document

## Introduction

This document addresses two critical bugs in the TaskTree intelligent reminder system that prevent users from properly configuring and testing their LLM connections. Bug #1 causes API connectivity tests to consistently fail with "Unknown provider: minimax" errors, while Bug #2 affects the persistence of analysis dimension configuration toggles after page refresh. These issues block users from validating their LLM setup and maintaining their preferred analysis settings.

## Bug Analysis

### Current Behavior (Defect)

**Bug #1: API Connectivity Test Failure**

1.1 WHEN a user clicks the "Test Connection" button in the Settings page with provider set to "minimax" THEN the system returns "Unknown provider: minimax" error after a long wait

1.2 WHEN the frontend sends `provider="minimax"` in the test connection request THEN the backend LLMService fails to match the provider and raises an exception

1.3 WHEN LLMService.__init__ is called with the default parameter `provider="minmax"` (typo) THEN there is a mismatch between the frontend value "minimax" and backend handling

**Bug #2: Analysis Dimension Configuration Persistence**

1.4 WHEN a user toggles analysis dimension switches (overdue, progress_stalled, dependency_unblocked, team_load, risk_prediction) and saves settings THEN the toggle states may not persist correctly after page refresh

1.5 WHEN the frontend loads settings and attempts to set nested form values using `setFieldsValue` with paths like `analysis_config.overdue` THEN the values are not properly restored

### Expected Behavior (Correct)

**Bug #1: API Connectivity Test Should Succeed**

2.1 WHEN a user clicks the "Test Connection" button with provider set to "minimax" and valid credentials THEN the system SHALL successfully call the LLM API and return connection success with response time

2.2 WHEN the frontend sends `provider="minimax"` in the test connection request THEN the backend SHALL correctly route to the `_call_minimax` method

2.3 WHEN LLMService processes provider names THEN it SHALL handle both "minimax" and "minmax" variants consistently (case-insensitive or dual matching)

**Bug #2: Analysis Dimension Configuration Should Persist**

2.4 WHEN a user toggles analysis dimension switches and saves settings THEN the system SHALL persist all toggle states to the database in the `analysis_config` JSON field

2.5 WHEN the frontend loads settings after page refresh THEN the system SHALL correctly restore all analysis dimension toggle states from the saved `analysis_config`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user configures other LLM providers (openai, anthropic, custom) THEN the system SHALL CONTINUE TO handle those providers correctly

3.2 WHEN a user saves other notification settings (dingtalk_webhook, llm_api_key, daily_limit) THEN the system SHALL CONTINUE TO persist those settings correctly

3.3 WHEN the LLM service makes actual API calls for task analysis THEN the system SHALL CONTINUE TO function with the corrected provider matching logic

3.4 WHEN a user interacts with other parts of the Settings page (profile, password, about tabs) THEN the system SHALL CONTINUE TO function normally

3.5 WHEN the backend creates or updates notification settings THEN the system SHALL CONTINUE TO properly encrypt API keys and handle all other fields

## Bug Condition Derivation

### Bug #1: Provider Name Mismatch

**Bug Condition Function:**
```pascal
FUNCTION isBugCondition_ProviderMismatch(X)
  INPUT: X of type TestConnectionRequest
  OUTPUT: boolean
  
  // Bug occurs when frontend sends "minimax" but backend expects exact match
  RETURN (X.provider = "minimax") AND 
         (backend_provider_check(X.provider) = false)
END FUNCTION
```

**Property Specification:**
```pascal
// Property: Fix Checking - Provider Name Matching
FOR ALL X WHERE isBugCondition_ProviderMismatch(X) DO
  result ← test_connection'(X)
  ASSERT result.success = true AND 
         result.error NOT CONTAINS "Unknown provider"
END FOR
```

### Bug #2: Analysis Config Persistence

**Bug Condition Function:**
```pascal
FUNCTION isBugCondition_ConfigPersistence(X)
  INPUT: X of type AnalysisConfigUpdate
  OUTPUT: boolean
  
  // Bug occurs when analysis_config contains toggle states
  RETURN X.analysis_config IS NOT NULL AND
         (saved_config = X.analysis_config) AND
         (loaded_config ≠ X.analysis_config after refresh)
END FUNCTION
```

**Property Specification:**
```pascal
// Property: Fix Checking - Config Persistence
FOR ALL X WHERE isBugCondition_ConfigPersistence(X) DO
  save_result ← save_settings'(X)
  loaded_result ← load_settings'()
  ASSERT loaded_result.analysis_config = X.analysis_config
END FOR
```

**Preservation Goal:**
```pascal
// Property: Preservation Checking
FOR ALL X WHERE NOT (isBugCondition_ProviderMismatch(X) OR 
                     isBugCondition_ConfigPersistence(X)) DO
  ASSERT F(X) = F'(X)
END FOR
```

This ensures that all other functionality (other providers, other settings fields, other API operations) continues to work identically after the fix.
