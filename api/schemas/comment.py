"""Pydantic request/response models for comment-related endpoints."""

from pydantic import BaseModel


class CommentOut(BaseModel):
    id: str
    text: str
    topic_label: str | None = None
    stance_label: str | None = None
