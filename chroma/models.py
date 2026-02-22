from pydantic import BaseModel


class CollectionResult(BaseModel):
    files: list[str]
    errors: list[str]
