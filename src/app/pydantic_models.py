from pydantic import BaseModel, Field

import app.configs as cfg


class HealthResponseExample(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"}, description="Status code.")
    serverTime: str = Field(
        ..., json_schema_extra={"example": "2025-09-21T16:33:05Z"}, description="Current server time in UTC."
    )
    serverName: str = Field(..., json_schema_extra={"example": cfg.SERVER_TITLE}, description="Server name.")


class CheckDBConnectionResponseExample(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"}, description="Status code.")
    serverTime: str = Field(
        ..., json_schema_extra={"example": "2025-09-21T16:33:05Z"}, description="Current server time in UTC."
    )
    databaseName: str = Field(..., json_schema_extra={"example": "dbmate"}, description="Database name.")
    message: str = Field(
        ..., json_schema_extra={"example": "Connection successful"}, description="Message information."
    )


class User(BaseModel):
    username: str = Field(..., example="testuser")
    password: str = Field(..., example="testpassword")
