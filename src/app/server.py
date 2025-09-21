from fastapi import (
    Depends,
    FastAPI,
)
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

import app.configs as cfg
from app.helpers.api import get_current_username
from app.helpers.common import get_now_as_utc
from app.helpers.db import test_connect_to_database
from app.pydantic_models import CheckDBConnectionResponseExample, HealthResponseExample
from app.versions import get_version

cfg.load_envs()

app = FastAPI(
    title=cfg.SERVER_TITLE,
    version=get_version(),
    description="API `dbmate` to create a database users",
)

app.add_middleware(HTTPSRedirectMiddleware)


# --- Default Endpoints ---
@app.get("/health", summary="Health check", response_model=HealthResponseExample)
async def health_check(username: str = Depends(get_current_username)):
    """
    Checks the health of the API. Requires basic authentication.
    """
    return {"status": "ok", "serverTime": get_now_as_utc(), "serverName": cfg.SERVER_TITLE}


# --- Default Endpoints ---
@app.get("/check-db-connection", summary="Checks database connection", response_model=CheckDBConnectionResponseExample)
async def health_check(username: str = Depends(get_current_username)):
    """
    Checks the health of the API. Requires basic authentication.
    """
    message = test_connect_to_database()
    return {"status": "ok", "serverTime": get_now_as_utc(), "databaseName": cfg.SERVER_TITLE, "message": message}
