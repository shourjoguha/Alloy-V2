# Error Response Documentation

## Error Response Format

All API errors follow a consistent structure:

```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
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

## Error Code Examples

### Not Found Errors (NF_)

#### NF_PROGRAM_001 - Program Not Found
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
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

**HTTP Status**: 404 Not Found

**Common Scenarios**:
- Program ID doesn't exist
- Program was deleted
- User doesn't have access to this program

**Troubleshooting**:
1. Verify the program ID is correct
2. Check if the program exists in the database
3. Verify the user has permissions to access the program

---

#### NF_MOVEMENT_001 - Movement Not Found
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "errors": [
    {
      "code": "NF_MOVEMENT_001",
      "message": "Movement not found",
      "details": {
        "id": 456
      }
    }
  ]
}
```

**HTTP Status**: 404 Not Found

---

### Authentication Errors (AUTH_)

#### AUTH_001 - Missing Authorization Header
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "errors": [
    {
      "code": "AUTH_001",
      "message": "No authorization header provided",
      "details": {}
    }
  ]
}
```

**HTTP Status**: 401 Unauthorized

**Troubleshooting**:
1. Add `Authorization: Bearer <token>` header
2. Ensure token is valid and not expired

---

#### AUTH_004 - Invalid or Expired Token
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "errors": [
    {
      "code": "AUTH_004",
      "message": "Invalid or expired token",
      "details": {}
    }
  ]
}
```

**HTTP Status**: 401 Unauthorized

**Troubleshooting**:
1. Refresh the access token
2. Re-authenticate the user
3. Check token expiration time

---

### Validation Errors (VAL_)

#### VAL_001 - Invalid Request Body
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "errors": [
    {
      "code": "VAL_001",
      "message": "Validation failed for program_name: This field is required",
      "details": {
        "field": "program_name",
        "constraint": "required"
      }
    }
  ]
}
```

**HTTP Status**: 400 Bad Request

---

### Business Rule Errors (BR_)

#### BR_001 - Invalid Program Duration
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "errors": [
    {
      "code": "BR_001",
      "message": "Program must be 8-12 weeks",
      "details": {
        "duration_weeks": 6,
        "min_weeks": 8,
        "max_weeks": 12
      }
    }
  ]
}
```

**HTTP Status**: 422 Unprocessable Entity

**Troubleshooting**:
1. Adjust duration to be between 8 and 12 weeks
2. Use an even number of weeks
3. Check program template constraints

---

## Handling Errors on the Client

### TypeScript Example

```typescript
interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

interface ErrorResponse {
  data: null;
  meta: {
    request_id: string;
    timestamp: string;
  };
  errors: APIError[];
}

async function handleAPIResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ErrorResponse = await response.json();
    
    // Handle not found errors
    if (error.errors[0].code.startsWith('NF_')) {
      navigateToNotFound();
      throw error;
    }
    
    // Handle authentication errors
    if (error.errors[0].code.startsWith('AUTH_')) {
      redirectToLogin();
      throw error;
    }
    
    // Handle validation errors
    if (error.errors[0].code.startsWith('VAL_')) {
      showValidationErrors(error.errors[0].details);
      throw error;
    }
    
    // Handle business rule errors
    if (error.errors[0].code.startsWith('BR_')) {
      showNotification(error.errors[0].message, 'warning');
      throw error;
    }
    
    throw error;
  }
  
  return response.json();
}
```

### Error Code Categories

| Prefix | Category | Handling Strategy |
|---------|-----------|-------------------|
| AUTH_ | Authentication | Redirect to login, refresh token |
| VAL_ | Validation | Show field-level errors, highlight invalid inputs |
| NF_ | Not Found | Show 404 page, navigate back |
| BR_ | Business Rule | Show warning message, suggest corrections |
| CF_ | Conflict | Show conflict message, offer resolution options |
| SYS_ | System | Show generic error, retry button, contact support |

## Request ID

Every error response includes a `request_id` in the `meta` object:

```json
{
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Use the request_id when**:
- Contacting support
- Reporting bugs
- Debugging production issues
- Correlating logs across services

## Best Practices

1. **Always check the errors array**: Multiple errors can be returned for validation failures
2. **Use the code field**: Implement code-specific handling logic
3. **Include request_id in logs**: Help with debugging and support
4. **Show user-friendly messages**: Use `message` for UI, `code` for logic
5. **Validate inputs client-side**: Prevent obvious validation errors before sending requests
