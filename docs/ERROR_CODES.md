# Error Code Standards

## Error Code Taxonomy

Error codes follow the format `{PREFIX}_{CODE}` where:
- `PREFIX`: Category abbreviation (AUTH, VAL, NF, BR, CF, SYS)
- `CODE`: Sequential number for the specific error

## AUTH - Authentication & Authorization

| Code | Description | HTTP Status |
|------|-------------|--------------|
| AUTH_001 | Missing authorization header | 401 |
| AUTH_002 | Invalid authentication scheme | 401 |
| AUTH_003 | Invalid authorization header format | 401 |
| AUTH_004 | Invalid or expired token | 401 |
| AUTH_005 | User not found | 401 |
| AUTH_006 | Insufficient permissions | 403 |
| AUTH_007 | Missing required role | 403 |
| AUTH_ADMIN_REQUIRED | Admin access required | 403 |
| AUTH_SUPER_ADMIN_REQUIRED | Super admin access required | 403 |
| AUTH_ACCOUNT_INACTIVE | Account is inactive | 403 |

## VAL - Validation Errors

| Code | Description | HTTP Status |
|------|-------------|--------------|
| VAL_001 | Invalid request body | 400 |
| VAL_002 | Missing required field | 400 |
| VAL_003 | Invalid field format | 400 |
| VAL_004 | Value out of range | 400 |
| VAL_005 | Invalid enum value | 400 |
| VAL_006 | Invalid date format | 400 |
| VAL_PASSWORD_WEAK | Password does not meet strength requirements | 400 |
| VAL_VERIFICATION_CODE_001 | Invalid 2FA verification code | 400 |
| VAL_ENABLE_CODE_001 | 2FA enable code invalid | 400 |
| VAL_STRUCTURED_RESPONSE_JSON_001 | No plan available to accept | 400 |
| VAL_PATTERN_001 | Movement has invalid pattern | 400 |
| VAL_RULE_TYPE_001 | Invalid rule type value | 400 |
| VAL_ACTIVITY_TYPE_001 | Invalid activity type value | 400 |
| VAL_DISCIPLINE_001 | Invalid discipline value | 400 |
| VAL_EMBEDDING_VECTOR_001 | Reference movement has no embedding vector | 400 |
| VAL_METABOLIC_DEMAND_001 | Invalid metabolic demand value | 400 |
| VAL_MOVEMENT_ID_001 | Movement ID must be provided | 400 |
| VAL_PROGRAM_ID_001 | Program ID validation failed | 400 |
| VAL_METHOD_001 | Method field validation failed | 400 |
| VAL_ENDPOINT_001 | Endpoint field validation failed | 400 |

## NF - Not Found Errors

| Code | Description | HTTP Status |
|------|-------------|--------------|
| NF_PROGRAM_001 | Program not found | 404 |
| NF_MOVEMENT_001 | Movement not found | 404 |
| NF_CIRCUIT_001 | Circuit template not found | 404 |
| NF_USER_001 | User not found | 404 |
| NF_SESSION_001 | Session not found | 404 |
| NF_MICROCYCLE_001 | Microcycle not found | 404 |
| NF_FAVORITE_001 | Favorite not found | 404 |
| NF_WORKOUTLOG_001 | Workout log not found | 404 |
| NF_CONVERSATIONTHREAD_001 | Conversation thread not found | 404 |
| NF_RULE_001 | Rule not found | 404 |
| NF_CONFIG_001 | Config not found | 404 |
| NF_ACTIVITY_001 | Activity not found | 404 |
| NF_MUSCLERECOVERYSTATE_001 | Muscle recovery state not found | 404 |
| NF_RECOVERYSIGNAL_001 | Recovery signal not found | 404 |
| NF_AUDITLOG_001 | Audit log not found | 404 |
| NF_USERERRORSUMMARY_001 | User error summary not found | 404 |

## BR - Business Rule Errors

| Code | Description | HTTP Status |
|------|-------------|--------------|
| BR_001 | Invalid program duration (must be 8-12 weeks) | 422 |
| BR_002 | Program must have even number of weeks | 422 |
| BR_003 | Invalid number of goals (1-3 required) | 422 |
| BR_004 | Goal weights must sum to 10 | 422 |
| BR_005 | Goal interference detected | 422 |
| BR_006 | Invalid split template for goals | 422 |
| BR_007 | Max sessions exceeded | 422 |
| BR_008 | Cannot delete active program | 422 |

## CF - Conflict Errors

| Code | Description | HTTP Status |
|------|-------------|--------------|
| CF_001 | Resource already exists | 409 |
| CF_002 | Concurrent modification conflict | 409 |
| CF_003 | Duplicate entry | 409 |

## SYS - System Errors

| Code | Description | HTTP Status |
|------|-------------|--------------|
| SYS_001 | Internal server error | 500 |
| SYS_002 | Database connection failed | 503 |
| SYS_003 | External service unavailable | 503 |
| SYS_004 | Configuration error | 500 |

## Usage Guidelines

### When to Create New Error Codes

1. **Check existing codes first**: Reuse existing codes when possible
2. **Add for new scenarios**: Create new codes for distinct error scenarios
3. **Document thoroughly**: Add description and HTTP status to this table
4. **Update client docs**: Ensure frontend teams have updated error code documentation

### Error Response Format

All error responses follow this structure:

```json
{
  "data": null,
  "meta": {
    "request_id": "uuid-here",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "errors": [
    {
      "code": "NF_PROGRAM_001",
      "message": "Program not found",
      "details": {
        "id": 123
      }
    }
  ]
}
```

### Client Error Handling

```typescript
// Example: Handling not found errors
if (error.code === 'NF_PROGRAM_001') {
  showNotification('Program not found', 'error');
  navigateToPrograms();
}

// Example: Handling validation errors
if (error.code.startsWith('VAL_')) {
  showValidationErrors(error.details);
}

// Example: Handling business rule errors
if (error.code.startsWith('BR_')) {
  showBusinessRuleViolation(error.message);
}
```
