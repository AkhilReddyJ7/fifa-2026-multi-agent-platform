from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChatMessageRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    role: str
    content: str
    agent_trace: list[Any] | None = None
    created_at: datetime


class ChatSessionRead(BaseModel):
    model_config = {"from_attributes": True}

    session_uuid: str
    user_id: str | None = None
    created_at: datetime
    messages: list[ChatMessageRead] = []
