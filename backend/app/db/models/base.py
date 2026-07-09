from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlmodel import SQLModel
from sqlmodel import Field


class DBBaseModel(SQLModel):
    """
    DB base model
    """
    create_time: datetime | None = Field(default=datetime.now, title="Created time")
    edit_time: datetime | None = Field(default=datetime.now, title="Updated time")
    # create_by: str | None = Field(default="", title="Created by")
    # update_by: str | None = Field(default="", title="Updated by")
