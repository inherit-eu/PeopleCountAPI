import os

from dotenv import load_dotenv
from fastapi import FastAPI
import logging

from fastapi.openapi.utils import get_openapi

from auth.authorization import JWTMiddleware, keycloak_client_id, keycloak_server_url, keycloak_realm
from route.people_counts import router as people_counts_router
from route.rooms import router as rooms_router
from route.liveview import router as liveview_router
from route.patterns import router as patterns_router
from fastapi.middleware.cors import CORSMiddleware

console_handler = logging.StreamHandler()

handlers = [console_handler]

logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
logger = logging.getLogger(__name__)

# Example log message
logger.info("Application started")

load_dotenv()
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]


app = FastAPI(docs_url="/people/docs", redoc_url=None, openapi_url="/people/docs/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # useful if you read auth headers etc
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Kondylaki People Monitoring API",
        version="1.0.0",
        description="People Monitoring API for Kondylaki",
        routes=app.routes,
    )

    # Only update securitySchemes, don't overwrite components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "oauth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"{keycloak_server_url}/realms/{keycloak_realm}/protocol/openid-connect/auth",
                    "tokenUrl": f"{keycloak_server_url}/realms/{keycloak_realm}/protocol/openid-connect/token",
                    "scopes": {}
                }
            }
        },
        "bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    # Add global security requirements
    openapi_schema["security"] = [
        {"oauth2": []},
        {"bearer": []}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.swagger_ui_init_oauth = {
    "clientId": keycloak_client_id
}

app.include_router(people_counts_router)
app.include_router(rooms_router)
app.include_router(liveview_router)
app.include_router(patterns_router)

is_dev = os.getenv("ENV", "unknown") == "development"
if not is_dev:
    app.add_middleware(JWTMiddleware)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_config=None)