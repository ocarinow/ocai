# Management HTTP API

Generated from the checked-in OpenAPI contract. The platform is a foundation
release: these operations do not provide inference or organization administration.
The service disables interactive `/docs`, `/redoc` and `/openapi.json` routes.

| Method | Path | Operation | Responses |
|---|---|---|---|
| `GET` | `/health/live` | `get_liveness` | 200 |
| `GET` | `/health/ready` | `get_readiness` | 503 |
| `GET` | `/management/v1/status` | `get_system_status` | 200 |

## Response schemas

```json
{
  "ErrorDetail": {
    "properties": {
      "code": {
        "title": "Code",
        "type": "string"
      },
      "message": {
        "title": "Message",
        "type": "string"
      },
      "request_id": {
        "title": "Request Id",
        "type": "string"
      }
    },
    "required": [
      "code",
      "message",
      "request_id"
    ],
    "title": "ErrorDetail",
    "type": "object"
  },
  "ErrorEnvelope": {
    "properties": {
      "error": {
        "$ref": "#/components/schemas/ErrorDetail"
      }
    },
    "required": [
      "error"
    ],
    "title": "ErrorEnvelope",
    "type": "object"
  },
  "Liveness": {
    "properties": {
      "status": {
        "const": "alive",
        "default": "alive",
        "title": "Status",
        "type": "string"
      }
    },
    "title": "Liveness",
    "type": "object"
  },
  "SystemStatus": {
    "properties": {
      "inference_ready": {
        "const": false,
        "default": false,
        "title": "Inference Ready",
        "type": "boolean"
      },
      "service": {
        "const": "ocai-gateway",
        "default": "ocai-gateway",
        "title": "Service",
        "type": "string"
      },
      "stage": {
        "const": "foundation",
        "default": "foundation",
        "title": "Stage",
        "type": "string"
      }
    },
    "title": "SystemStatus",
    "type": "object"
  }
}
```

The [platform guide](../platform/README.md) explains readiness and error handling.
