from typing import List, Literal

from pydantic import BaseModel, Field


class Route(BaseModel):
    target: Literal["structured", "documents", "both", "out_of_scope"]
    reason: str = Field(max_length=300)


class Concepts(BaseModel):
    concepts: List[str] = Field(default_factory=list, max_length=6)


class SqlDraft(BaseModel):
    sql: str = Field(min_length=6, max_length=8000)
    datasets: List[str] = Field(default_factory=list)
    measures_used: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
