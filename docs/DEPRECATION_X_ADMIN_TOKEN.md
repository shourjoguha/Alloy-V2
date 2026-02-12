# X-Admin-Token Deprecation Guide

## Overview

The `X-Admin-Token` authentication method is **deprecated** and will be removed in version **3.0.0**. Please migrate to JWT-based authentication with role-based access control (RBAC).

## Deprecation Timeline

| Version | Status |
|---------|--------|
| v2.0.0 (current) | Deprecated with warnings |
| v2.1.0 | Warnings, documentation updated |
| v3.0.0 | X-Admin-Token removed |

## Migration Steps

### Step 1: Update Authentication Method

**Before (Deprecated):**
```python
import requests

headers = {
    "X-Admin-Token": "your_admin_token"
}

response = requests.get(
    "https://api.alloy.com/circuits/admin/1",
    headers=headers
)
```

**After (Recommended):**
```python
import requests

# First, authenticate to get JWT token
auth_response = requests.post(
    "https://api.alloy.com/auth/login",
    json={
        "email": "admin@example.com",
        "password": "your_password"
    }
)

access_token = auth_response.json()["data"]["access_token"]

# Use JWT for authenticated requests
headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "https://api.alloy.com/circuits/admin/1",
    headers=headers
)
```

### Step 2: Configure Admin Role

Ensure your admin user has the `ADMIN` or `SUPER_ADMIN` role in the database:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

### Step 3: Update Client Code

Replace all `X-Admin-Token` headers with `Authorization: Bearer <token>` headers:

**Old Pattern:**
```python
headers = {"X-Admin-Token": settings.ADMIN_TOKEN}
```

**New Pattern:**
```python
headers = {"Authorization": f"Bearer {access_token}"}
```

### Step 4: Handle Deprecation Warnings

API responses will include deprecation headers:

```
X-Deprecation: Use JWT with admin role
X-Deprecation-Message: X-Admin-Token will be removed in version 3.0.0
```

Update your logging to detect and report these warnings.

### Step 5: Remove Admin Token Configuration

After successful migration, remove the admin token configuration from your environment:

```bash
# Remove from .env
unset ADMIN_API_TOKEN

# Or remove from environment
unset ADMIN_API_TOKEN
```

## Benefits of Migration

1. **Security**: JWT tokens have built-in expiration and can be revoked
2. **Flexibility**: Support for multiple admin roles (ADMIN, SUPER_ADMIN)
3. **Standardization**: Follows OAuth2/JWT industry standards
4. **Audit Trail**: All admin actions can be traced to specific users
5. **Scalability**: No shared secrets across multiple services

## Role-Based Access Control

### Available Roles

| Role | Permissions |
|-------|-------------|
| `USER` | Standard user access |
| `ADMIN` | Administrative access (manage circuits, scoring config) |
| `SUPER_ADMIN` | Full system access (user management, system config) |

### Role Enforcement

Endpoints that previously required `X-Admin-Token` now require specific roles:

```python
from app.api.routes.dependencies import require_role, get_current_user
from app.models.user import UserRole

@router.get("/admin/circuits/{circuit_id}")
@require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
async def get_circuit_admin(
    circuit_id: int,
    current_user: User = Depends(get_current_user)
):
    # Only users with ADMIN or SUPER_ADMIN role can access
    return await circuit_service.get_circuit(circuit_id)
```

## Error Handling

### 401 Unauthorized (Invalid Token)
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {}
  }]
}
```

### 403 Forbidden (Insufficient Role)
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "AUTH_FORBIDDEN",
    "message": "Requires one of roles: ['admin', 'super_admin']",
    "details": {
      "required_roles": ["admin", "super_admin"],
      "user_role": "user"
    }
  }]
}
```

## Testing

### Test Script

```python
import requests

BASE_URL = "https://api.alloy.com"

# Step 1: Login
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": "admin@example.com",
        "password": "your_password"
    }
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

access_token = login_response.json()["data"]["access_token"]
print(f"✓ Logged in successfully")

# Step 2: Test admin endpoint
headers = {"Authorization": f"Bearer {access_token}"}

circuit_response = requests.get(
    f"{BASE_URL}/circuits/admin/1",
    headers=headers
)

if circuit_response.status_code == 200:
    print(f"✓ Admin endpoint accessible")
else:
    print(f"✗ Admin endpoint failed: {circuit_response.text}")

# Step 3: Test regular user endpoint (should fail with admin token)
user_response = requests.get(
    f"{BASE_URL}/circuits/1",
    headers=headers
)

if user_response.status_code == 200:
    print(f"✓ Public endpoint accessible")
else:
    print(f"✗ Public endpoint failed: {user_response.text}")
```

## Support

For questions or assistance with migration:
- Documentation: [API Endpoints](API_ENDPOINTS.md)
- Error Codes: [Error Codes](ERROR_CODES.md)
- Contact: support@alloy.com

## Checklist

Use this checklist to track your migration progress:

- [ ] Update authentication to use JWT tokens
- [ ] Configure admin roles in database
- [ ] Replace all `X-Admin-Token` headers with `Authorization: Bearer <token>`
- [ ] Update error handling for 401/403 responses
- [ ] Add token refresh logic (tokens expire after 1 hour)
- [ ] Test all admin endpoints with new authentication
- [ ] Remove `ADMIN_API_TOKEN` from configuration
- [ ] Update monitoring/alerting to detect deprecation warnings
- [ ] Document migration for team members
- [ ] Deploy to staging environment
- [ ] Conduct smoke testing
- [ ] Deploy to production
