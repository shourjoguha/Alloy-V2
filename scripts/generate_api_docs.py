#!/usr/bin/env python3
"""Generate interactive API documentation from OpenAPI spec."""
import json
from pathlib import Path
from typing import Any


def generate_openapi_spec() -> dict:
    """Generate OpenAPI 3.0 specification."""
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Alloy API",
            "description": "RESTful API for the Alloy training program platform",
            "version": "1.0.0",
            "contact": {
                "name": "Alloy Support",
                "email": "support@alloy.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.alloy.com",
                "description": "Production server"
            }
        ],
        "tags": [
            {"name": "Authentication", "description": "User authentication and token management"},
            {"name": "Programs", "description": "Training program management"},
            {"name": "Settings", "description": "User settings and preferences"},
            {"name": "Circuits", "description": "Circuit template management"},
            {"name": "Health", "description": "System health monitoring"},
            {"name": "Metrics", "description": "Performance and usage metrics"},
            {"name": "Two-Factor Auth", "description": "2FA setup and management"},
            {"name": "Performance", "description": "Performance monitoring"},
            {"name": "Audit Logs", "description": "Security and activity auditing"}
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "AdminToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Admin-Token",
                    "description": "DEPRECATED: Use BearerAuth instead",
                    "x-deprecated": True
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Error code"},
                        "message": {"type": "string", "description": "Error message"},
                        "details": {"type": "object", "description": "Additional error details"}
                    }
                },
                "APIResponse": {
                    "type": "object",
                    "properties": {
                        "data": {"description": "Response data"},
                        "meta": {
                            "type": "object",
                            "properties": {
                                "request_id": {"type": "string"},
                                "timestamp": {"type": "string", "format": "date-time"}
                            }
                        },
                        "errors": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "LoginRequest": {
                    "type": "object",
                    "required": ["email", "password"],
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string", "minLength": 8}
                    }
                },
                "LoginResponse": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string"},
                        "refresh_token": {"type": "string"},
                        "token_type": {"type": "string", "enum": ["bearer"]},
                        "expires_in": {"type": "integer", "description": "Seconds until expiration"}
                    }
                },
                "ProgramCreate": {
                    "type": "object",
                    "required": ["name", "duration_weeks", "goals", "split_template", "progression_style", "max_session_duration"],
                    "properties": {
                        "name": {"type": "string"},
                        "duration_weeks": {"type": "integer", "minimum": 8, "maximum": 12},
                        "goals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "goal_type": {"type": "string"},
                                    "weight": {"type": "number"}
                                }
                            }
                        },
                        "split_template": {"type": "string"},
                        "progression_style": {"type": "string"},
                        "max_session_duration": {"type": "integer", "description": "Target session duration in minutes"},
                        "persona": {
                            "type": "object",
                            "properties": {
                                "age_range": {"type": "string"},
                                "experience_level": {"type": "string"}
                            }
                        }
                    }
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "uptime_seconds": {"type": "number"},
                        "database": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string"},
                                "primary": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "response_time_ms": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return spec


def generate_swagger_html() -> str:
    """Generate Swagger UI HTML page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Alloy API - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui.css">
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .swagger-ui .topbar { display: none; }
        .api-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .api-header h1 { margin: 0; font-size: 2em; }
        .api-header p { margin: 10px 0 0; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="api-header">
        <h1>Alloy API Documentation</h1>
        <p>Interactive API documentation powered by Swagger UI</p>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                docExpansion: "list",
                filter: true,
                showRequestHeaders: true,
                tryItOutEnabled: true,
                persistAuthorization: true,
                requestInterceptor: function(request) {
                    const token = localStorage.getItem('access_token');
                    if (token) {
                        request.headers.Authorization = 'Bearer ' + token;
                    }
                    return request;
                }
            });
        };
        
        // Helper function to set auth token
        window.setAuthToken = function(token) {
            localStorage.setItem('access_token', token);
            console.log('Auth token set');
        };
    </script>
</body>
</html>"""


def generate_redoc_html() -> str:
    """Generate ReDoc HTML page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Alloy API - ReDoc</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.css">
</head>
<body>
    <redoc spec-url="/openapi.json"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>"""


def generate_readme_docs() -> str:
    """Generate README for API documentation."""
    return """# Alloy API Documentation

## Interactive Documentation

### Swagger UI
[Open Swagger UI](/docs) - Interactive API explorer with try-it-out functionality

### ReDoc
[Open ReDoc](/redoc) - Clean, responsive API documentation

## Quick Start

### 1. Get Your Token
```bash
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "your_password"}'
```

Save the `access_token` from the response.

### 2. Make Authenticated Requests
```bash
curl http://localhost:8000/programs \\
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
curl -X POST http://localhost:8000/auth/refresh \\
  -H "Content-Type: application/json" \\
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
openapi-generator-cli generate \\
  -i openapi.json \\
  -g typescript-axios \\
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
"""


def generate_docs() -> None:
    """Generate all API documentation files."""
    
    docs_dir = Path(__file__).parent.parent / "docs" / "api"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate OpenAPI spec
    spec = generate_openapi_spec()
    spec_path = docs_dir / "openapi.json"
    spec_path.write_text(json.dumps(spec, indent=2))
    print(f"✓ Generated OpenAPI spec: {spec_path}")
    
    # Generate Swagger UI HTML
    swagger_html = generate_swagger_html()
    swagger_path = docs_dir / "swagger.html"
    swagger_path.write_text(swagger_html)
    print(f"✓ Generated Swagger UI: {swagger_path}")
    
    # Generate ReDoc HTML
    redoc_html = generate_redoc_html()
    redoc_path = docs_dir / "redoc.html"
    redoc_path.write_text(redoc_html)
    print(f"✓ Generated ReDoc: {redoc_path}")
    
    # Generate README
    readme_content = generate_readme_docs()
    readme_path = docs_dir / "README.md"
    readme_path.write_text(readme_content)
    print(f"✓ Generated API README: {readme_path}")
    
    print(f"\n📚 API documentation generated in: {docs_dir}")


if __name__ == "__main__":
    generate_docs()
