# Alloy API Documentation

## Interactive Documentation

### Swagger UI
[Open Swagger UI](/docs) - Interactive API explorer with try-it-out functionality

### ReDoc
[Open ReDoc](/redoc) - Clean, responsive API documentation

## Quick Start

### 1. Get Your Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your_password"}'
```

Save the `access_token` from the response.

### 2. Make Authenticated Requests
```bash
curl http://localhost:8000/programs \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Try It Out
Visit [Swagger UI](/docs) and click "Authorize" to enter your token, then use the "Try it out" button for any endpoint.

## Authentication

### JWT Token
Most endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```

### Refresh Token
Access tokens expire after 1 hour. Use the refresh endpoint to get a new token:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Rate Limiting

| Endpoint Type | Limit | Window |
|--------------|--------|---------|
| Read operations | 100 requests | 1 minute |
| Write operations | 10 requests | 1 minute |
| Auth endpoints | 5 requests | 1 minute |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit for the window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid email or password |
| `AUTH_EXPIRED_TOKEN` | 401 | Token has expired |
| `NF_PROGRAM` | 404 | Program not found |
| `VAL_DURATION_WEEKS` | 422 | Duration must be 8-12 weeks |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

## Pagination

List endpoints support cursor-based pagination:

```bash
curl "http://localhost:8000/programs?cursor=abc123&limit=20"
```

Response includes:
- `next_cursor`: Cursor for next page
- `prev_cursor`: Cursor for previous page
- `has_more`: Boolean indicating more results available

## Client Libraries

### Python
Generated Python client available in [client/alloy_api_client.py](../client/alloy_api_client.py)

```python
from client.alloy_api_client import AlloyClient

client = AlloyClient(base_url="http://localhost:8000")
client.login(email="user@example.com", password="password")

programs = client.list_programs()
print(programs)
```

### JavaScript/TypeScript
Generate a TypeScript client using the OpenAPI spec:

```bash
openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-axios \
  -o client/typescript
```

## Development

### Generate Documentation
```bash
python scripts/generate_api_docs.py
```

### Regenerate OpenAPI Spec
```bash
python scripts/generate_api_docs.py
```

### Update Interactive Docs
The interactive documentation pages are auto-generated from the OpenAPI spec.

## Support

- Documentation: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Error Codes: [ERROR_CODES.md](ERROR_CODES.md)
- Email: support@alloy.com
