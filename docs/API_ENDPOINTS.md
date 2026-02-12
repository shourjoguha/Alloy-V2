# API Endpoint Documentation

This document provides comprehensive documentation for all Alloy API endpoints.

## Table of Contents

- [Authentication](#authentication)
- [Programs](#programs)
- [Settings](#settings)
- [Circuits](#circuits)
- [Health](#health)
- [Metrics](#metrics)
- [Two-Factor Authentication](#two-factor-authentication)
- [Performance](#performance)
- [Audit Logs](#audit-logs)

---

## Base URL

```
Production: https://api.alloy.com
Development: http://localhost:8000
```

## Authentication

All API endpoints (except `/health`, `/metrics`) require authentication via JWT tokens.

### Authentication Header

```
Authorization: Bearer <access_token>
```

### Login Endpoint

#### POST `/auth/login`

Authenticate with email and password to receive access and refresh tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password123"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-02-11T10:30:00Z"
  },
  "errors": []
}
```

**Error Response (401 Unauthorized):**
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

#### POST `/auth/refresh`

Refresh an access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Programs

### Create Program

#### POST `/programs`

Create a new training program with immediate skeleton response.

**Authentication:** Required (JWT)  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "Strength Training Program",
  "duration_weeks": 8,
  "goals": [
    {
      "goal_type": "strength",
      "weight": 5
    },
    {
      "goal_type": "muscle_gain",
      "weight": 3
    },
    {
      "goal_type": "endurance",
      "weight": 2
    }
  ],
  "split_template": "push_pull_legs",
  "progression_style": "linear",
  "max_session_duration": 60,
  "persona": {
    "age_range": "25-34",
    "experience_level": "intermediate"
  },
  "movement_rules": [
    {
      "movement_id": 1,
      "is_preferred": true,
      "notes": "Keep this exercise"
    }
  ],
  "enjoyable_activities": [
    {
      "activity_type": "running",
      "custom_name": null
    },
    {
      "activity_type": "custom",
      "custom_name": "hiking"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": 123,
    "user_id": 456,
    "name": "Strength Training Program",
    "duration_weeks": 8,
    "goals": [...],
    "split_template": "push_pull_legs",
    "progression_style": "linear",
    "is_active": true,
    "created_at": "2026-02-11T10:30:00Z",
    "microcycles": [
      {
        "id": 789,
        "program_id": 123,
        "week_number": 1,
        "focus_area": "upper_body",
        "sessions": [
          {
            "id": 101,
            "microcycle_id": 789,
            "day_of_week": "monday",
            "target_duration": 60,
            "exercises": []
          }
        ]
      }
    ]
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

**Error Response (422 Unprocessable Entity):**
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "VAL_DURATION_WEEKS",
    "message": "Validation failed for duration_weeks: must be between 8 and 12",
    "details": {
      "field": "duration_weeks",
      "min": 8,
      "max": 12,
      "actual": 6
    }
  }]
}
```

### List Programs

#### GET `/programs`

Get all programs for the current user.

**Authentication:** Required (JWT)  
**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `is_active` | boolean | null | Filter by active status |
| `limit` | integer | 20 | Maximum number of results |
| `offset` | integer | 0 | Number of results to skip |

**Response (200 OK):**
```json
{
  "data": {
    "items": [
      {
        "id": 123,
        "name": "Strength Training Program",
        "duration_weeks": 8,
        "is_active": true,
        "created_at": "2026-02-11T10:30:00Z"
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0,
    "has_next": false,
    "has_prev": false
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Get Program

#### GET `/programs/{program_id}`

Get a specific program by ID.

**Authentication:** Required (JWT)  
**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|-------|----------|-------------|
| `program_id` | integer | Yes | Program ID |

**Response (200 OK):**
```json
{
  "data": {
    "id": 123,
    "user_id": 456,
    "name": "Strength Training Program",
    "duration_weeks": 8,
    "goals": [...],
    "split_template": "push_pull_legs",
    "progression_style": "linear",
    "is_active": true,
    "created_at": "2026-02-11T10:30:00Z",
    "microcycles": [...],
    "sessions": [...]
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

**Error Response (404 Not Found):**
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "NF_PROGRAM",
    "message": "Program not found",
    "details": {
      "program_id": 123
    }
  }]
}
```

### Update Program

#### PATCH `/programs/{program_id}`

Update an existing program.

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "name": "Updated Program Name",
  "is_active": false
}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": 123,
    "name": "Updated Program Name",
    "is_active": false,
    ...
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Delete Program

#### DELETE `/programs/{program_id}`

Delete a program.

**Authentication:** Required (JWT)

**Response (204 No Content)**

---

## Settings

### Get User Settings

#### GET `/settings/user`

Get current user settings.

**Authentication:** Required (JWT)

**Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "user_id": 456,
    "active_e1rm_formula": "brzycki",
    "use_metric": true
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Update User Settings

#### PATCH `/settings/user`

Update current user settings.

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "active_e1rm_formula": "epley",
  "use_metric": false
}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "user_id": 456,
    "active_e1rm_formula": "epley",
    "use_metric": false
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Get User Profile

#### GET `/settings/user/profile`

Get current user profile.

**Authentication:** Required (JWT)

**Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "user_id": 456,
    "height_cm": 180,
    "weight_kg": 75,
    "date_of_birth": "1990-01-15",
    "gender": "male"
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### List Movements

#### GET `/settings/movements`

List all available movements with optional filtering.

**Authentication:** Required (JWT)  
**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `pattern` | string | null | Filter by movement pattern |
| `discipline` | string | null | Filter by discipline |
| `equipment` | string | null | Filter by equipment type |
| `limit` | integer | 20 | Maximum number of results |
| `offset` | integer | 0 | Number of results to skip |

**Response (200 OK):**
```json
{
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Barbell Squat",
        "pattern": "squat",
        "discipline": "strength",
        "equipment": "barbell",
        "muscles": ["quadriceps", "glutes", "hamstrings"]
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Query Movements

#### POST `/settings/movements/query`

Advanced movement query with structured filtering.

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "filters": [
    {
      "field": "pattern",
      "operator": "eq",
      "value": "squat"
    },
    {
      "field": "discipline",
      "operator": "in",
      "value": ["strength", "power"]
    }
  ],
  "sort_by": "name",
  "sort_order": "asc",
  "limit": 20,
  "offset": 0
}
```

**Response (200 OK):**
```json
{
  "data": {
    "items": [...],
    "total": 15,
    "limit": 20,
    "offset": 0
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Circuits

### List Circuits

#### GET `/circuits`

List all circuit templates.

**Authentication:** None (Public)  
**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `circuit_type` | string | null | Filter by circuit type |

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Full Body HIIT",
      "circuit_type": "hiit",
      "duration_minutes": 30,
      "exercises": [...]
    }
  ],
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Get Circuit

#### GET `/circuits/{circuit_id}`

Get a specific circuit template.

**Authentication:** None (Public)

**Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "name": "Full Body HIIT",
    "circuit_type": "hiit",
    "duration_minutes": 30,
    "exercises": [...]
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Health

### Health Check

#### GET `/health`

Public health check endpoint for monitoring.

**Authentication:** None

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T10:30:00Z",
  "uptime_seconds": 123456.78,
  "database": {
    "status": "healthy",
    "primary": {
      "status": "healthy",
      "response_time_ms": 5.2,
      "healthy": true
    },
    "replicas": null,
    "response_time_ms": 5.2
  },
  "cache": {
    "status": "healthy",
    "response_time_ms": 1.5,
    "connected": true
  },
  "version": "1.0.0"
}
```

### Detailed Health Check

#### GET `/health/detailed`

Detailed health check (requires authentication).

**Authentication:** Required (JWT)

**Response (200 OK):** Same as `/health` but includes additional details.

### Database Health

#### GET `/health/database`

Database-specific health check.

**Authentication:** None

**Response (200 OK):**
```json
{
  "status": "healthy",
  "primary": {
    "status": "healthy",
    "response_time_ms": 5.2
  },
  "replicas": {
    "enabled": true,
    "strategy": "round_robin",
    "replicas": [
      {
        "url": "postgresql://...",
        "is_healthy": true,
        "last_check": "2026-02-11T10:30:00Z",
        "failure_count": 0,
        "last_error": null,
        "total_queries": 1234,
        "failed_queries": 5,
        "success_rate": 99.6
      }
    ],
    "healthy_count": 1,
    "total_count": 1
  },
  "timestamp": "2026-02-11T10:30:00Z"
}
```

### Readiness Check

#### GET `/health/readiness`

Kubernetes readiness probe.

**Response (200 OK):**
```json
{
  "status": "ready"
}
```

**Response (503 Service Unavailable):** Database not ready.

### Liveness Check

#### GET `/health/liveness`

Kubernetes liveness probe.

**Response (200 OK):**
```json
{
  "status": "alive"
}
```

---

## Metrics

### Get Metrics

#### GET `/metrics`

Prometheus metrics endpoint.

**Authentication:** None (but typically restricted to internal monitoring)

**Response:** Prometheus text format

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/programs",status="200"} 1234
http_requests_total{method="POST",endpoint="/programs",status="201"} 56

# HELP db_pool_size Current size of connection pool
# TYPE db_pool_size gauge
db_pool_size{pool="default"} 10
```

---

## Two-Factor Authentication

### Setup 2FA

#### POST `/auth/2fa/setup`

Initialize two-factor authentication setup.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Response (200 OK):**
```json
{
  "data": {
    "qr_code": "data:image/png;base64,...",
    "secret": "JBSWY3DPEHPK3PXP",
    "backup_codes": ["ABC123", "DEF456", ...]
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Verify 2FA

#### POST `/auth/2fa/verify`

Verify two-factor authentication code.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Request Body:**
```json
{
  "code": "123456"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "verified": true
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Enable 2FA

#### POST `/auth/2fa/enable`

Enable two-factor authentication after verification.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Response (200 OK):**
```json
{
  "data": {
    "enabled": true
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

### Disable 2FA

#### POST `/auth/2fa/disable`

Disable two-factor authentication.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Response (200 OK):**
```json
{
  "data": {
    "disabled": true
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Performance

### Get Performance Stats

#### GET `/performance/stats`

Get performance metrics and statistics.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `period` | string | "24h" | Time period (1h, 6h, 24h, 7d, 30d) |

**Response (200 OK):**
```json
{
  "data": {
    "period": "24h",
    "p50_latency_ms": 45.2,
    "p95_latency_ms": 120.5,
    "p99_latency_ms": 250.8,
    "total_requests": 12345,
    "error_rate": 0.12,
    "cache_hit_rate": 85.3,
    "db_query_time_avg_ms": 8.5
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Audit Logs

### List Audit Logs

#### GET `/audit/logs`

Get audit log entries.

**Authentication:** Required (JWT)  
**Role Required:** Admin

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|-------|---------|-------------|
| `user_id` | integer | null | Filter by user ID |
| `action_type` | string | null | Filter by action type |
| `limit` | integer | 50 | Maximum number of results |
| `offset` | integer | 0 | Number of results to skip |

**Response (200 OK):**
```json
{
  "data": {
    "items": [
      {
        "id": 1,
        "user_id": 456,
        "action_type": "login",
        "resource_type": "user",
        "resource_id": 456,
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "timestamp": "2026-02-11T10:30:00Z"
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid email or password |
| `AUTH_EXPIRED_TOKEN` | 401 | Token has expired |
| `AUTH_MISSING_TOKEN` | 401 | Authorization header required |
| `AUTH_FORBIDDEN` | 403 | Insufficient permissions |
| `NF_PROGRAM` | 404 | Program not found |
| `NF_SESSION` | 404 | Session not found |
| `NF_MOVEMENT` | 404 | Movement not found |
| `NF_CIRCUIT` | 404 | Circuit not found |
| `NF_USER` | 404 | User not found |
| `VAL_INVALID_DURATION` | 400 | Invalid duration value |
| `VAL_DURATION_WEEKS` | 422 | Duration must be between 8 and 12 weeks |
| `BR_PROGRAM_ACTIVE` | 409 | Cannot delete active program |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limiting

API endpoints are rate-limited based on endpoint type:

| Endpoint Type | Limit | Window |
|--------------|--------|---------|
| Read operations | 100 requests | 1 minute |
| Write operations | 10 requests | 1 minute |
| Auth endpoints | 5 requests | 1 minute |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1644576000
```

---

## Pagination

List endpoints support cursor-based pagination:

**Request:**
```
GET /programs?cursor=eyJmIjoxNjY1NDU1NjgwMH0iLCJ2IjoiY3JlYXRlZF9hdCJ9&limit=20
```

**Response:**
```json
{
  "data": {
    "items": [...],
    "next_cursor": "eyJmIjoxNjY1NDU1NjgwMH0iLCJ2IjoiY3JlYXRlZF9hdCJ9",
    "prev_cursor": null,
    "has_more": true
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": []
}
```

---

## Versioning

The current API version is **v1.0.0**.

Version information is included in responses and can be queried via `/health` endpoint.

---

## Changelog

| Version | Date | Changes |
|---------|--------|---------|
| 1.0.0 | 2026-02-11 | Initial release with complete API coverage |
