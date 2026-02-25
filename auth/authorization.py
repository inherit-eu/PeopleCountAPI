from typing import List

from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, OAuth2AuthorizationCodeBearer
import logging
import os
from keycloak import KeycloakOpenID # pip require python-keycloak
from pydantic import BaseModel
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


security = HTTPBearer(auto_error=False)
logging.basicConfig(level=logging.INFO, format="%(levelname)-9s %(asctime)s - %(name)s - %(message)s")
LOGGER = logging.getLogger(__name__)

keycloak_server_url = os.getenv("KEYCLOAK_SERVER_URL", "https://keycloak-inherit.euinno.eu")
keycloak_realm = os.getenv("KEYCLOAK_REALM", "INHERIT")
keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "SLG")

class User(BaseModel):
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    realm_roles: list
    client_roles: list
    pilots: List[int]

class authConfiguration(BaseModel):
    server_url: str
    realm: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str

settings = authConfiguration(
    server_url=keycloak_server_url,
    realm=keycloak_realm,
    client_id=keycloak_client_id,
    client_secret="",
    authorization_url=f"{keycloak_server_url}/realms/{keycloak_realm}/protocol/openid-connect/auth",
    token_url=f"{keycloak_server_url}/realms/{keycloak_realm}/protocol/openid-connect/token",
)


# This is used for fastapi docs authentification
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=settings.authorization_url, # https://sso.example.com/auth/
    tokenUrl=settings.token_url, # https://sso.example.com/auth/realms/example-realm/protocol/openid-connect/token
)

# This actually does the auth checks
# client_secret_key is not mandatory if the client is public on keycloak
keycloak_openid = KeycloakOpenID(
    server_url=settings.server_url, # https://sso.example.com/auth/
    client_id=settings.client_id, # backend-client-id
    realm_name=settings.realm, # example-realm
    client_secret_key=settings.client_secret, # your backend client secret
    verify=True,

)

async def get_oidc_public_key():
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{keycloak_openid.public_key()}"
        "\n-----END PUBLIC KEY-----"
    )

async def get_payload(token:str) -> dict:
    try:
        public_key= await get_oidc_public_key()
        return jwt.decode(token, public_key, algorithms=["RS256"], audience="account")
    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e), # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # List of (method, path) or just path to exclude from auth
        excluded_paths = [
            ("/people/docs", "GET"),
            ("/openapi.json", "GET"),
            ("/", "OPTIONS")
        ]

        # Check if the current request should be excluded
        for path, method in excluded_paths:
            if request.url.path.startswith(path) and request.method == method:
                return await call_next(request)

        pilot = request.headers.get("x-pilot")
        authorization: str = request.headers.get("Authorization")
        if authorization:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() == "bearer":
                try:
                    # Decode the JWT token
                    user_info = await get_user_info(await get_payload(token))
                    request.state.user = user_info  # Attach payload to request state

                    if pilot is not None:
                        pilot_id = int(pilot)
                        if pilot_id not in user_info.pilots:
                            return JSONResponse(status_code=403, content={"detail": "Unauthorized for pilot"})

                except Exception as e:
                    LOGGER.exception(e)
                    return JSONResponse(status_code=401, content={"detail": "Invalid token"})
            else:
                return JSONResponse(status_code=401, content={"detail": "Invalid scheme"})
        else:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        # Proceed to the next middleware or endpoint
        response = await call_next(request)
        return response

async def get_user_info(payload:dict) -> User:
    try:
        return User(
            id=payload.get("sub"),
            username=payload.get("preferred_username"),
            email=payload.get("email"),
            first_name=payload.get("given_name"),
            last_name=payload.get("family_name"),
            realm_roles=payload.get("realm_access", {}).get("roles", []),
            client_roles=payload.get("realm_access", {}).get("roles", []),
            pilots=[int(group.split('-')[1]) for group in payload.get("user_groups",[]) if group.startswith('pilot-')]
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e), # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
