from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Union

from bson import ObjectId
from pydantic import BaseModel, Field, ValidationError, field_validator


class PydanticObjectId(ObjectId):
    """
    Helper type to allow Pydantic to parse/validate MongoDB ObjectId values.

    This extends bson.ObjectId but provides Pydantic validators so fields
    using this type can accept str/ObjectId and always serialize as str.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> "PydanticObjectId":
        """
        Validate and convert the incoming value to a PydanticObjectId.
        Accepts ObjectId instances or strings that represent a valid ObjectId.
        """
        if isinstance(v, ObjectId):
            return cls(str(v))
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return cls(v)
            raise ValueError("Invalid ObjectId string")
        raise TypeError("ObjectId must be provided as str or ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide JSON schema for the custom type so OpenAPI shows it as string.
        """
        return {"type": "string", "title": "ObjectId", "examples": ["60f7f9f9f9f9f9f9f9f9f9f9"]}


def _ensure_non_empty(value: str, field_name: str) -> str:
    """
    Utility to ensure provided string is not empty or just whitespace.
    """
    if value is None:
        raise ValueError(f"{field_name} cannot be null")
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if value.strip() == "":
        raise ValueError(f"{field_name} cannot be empty")
    return value


# PUBLIC_INTERFACE
class NoteIn(BaseModel):
    """Payload model used when creating a note."""

    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content/body of the note")

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty or whitespace."""
        return _ensure_non_empty(v, "title")


# PUBLIC_INTERFACE
class NoteUpdate(BaseModel):
    """Payload model used when updating a note; all fields optional."""

    title: Optional[str] = Field(None, description="Updated title of the note")
    content: Optional[str] = Field(None, description="Updated content/body of the note")

    @field_validator("title")
    @classmethod
    def validate_optional_title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """If provided, ensure title is not empty or whitespace."""
        if v is None:
            return v
        return _ensure_non_empty(v, "title")


# PUBLIC_INTERFACE
class NoteOut(BaseModel):
    """Response model representing a note as returned by the API."""

    id: str = Field(..., description="Unique identifier of the note (stringified ObjectId)")
    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content/body of the note")
    createdAt: datetime = Field(..., description="Timestamp when the note was created")
    updatedAt: datetime = Field(..., description="Timestamp of the last update to the note")

    model_config = {
        "json_encoders": {ObjectId: str, PydanticObjectId: str},
        "populate_by_name": True,
    }

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty or whitespace."""
        return _ensure_non_empty(v, "title")


# PUBLIC_INTERFACE
def mongo_doc_to_note_out(doc: Dict[str, Any]) -> NoteOut:
    """
    Convert a MongoDB document into a NoteOut model.

    Expected document structure:
      {
        "_id": ObjectId | str,
        "title": str,
        "content": str,
        "createdAt": datetime | str,
        "updatedAt": datetime | str
      }

    Returns:
        NoteOut: Converted response model.

    Raises:
        KeyError: If required fields are missing.
        ValidationError: If the resulting model fails validation.
    """
    if doc is None:
        raise ValueError("Document cannot be None")

    _id_val: Union[str, ObjectId] = doc.get("_id")
    if isinstance(_id_val, ObjectId):
        id_str = str(_id_val)
    elif isinstance(_id_val, str):
        # validate string id looks like an ObjectId, but still accept it
        if ObjectId.is_valid(_id_val):
            id_str = _id_val
        else:
            # Accept non-ObjectId strings but keep them as-is; this keeps utility generic
            id_str = _id_val
    else:
        raise KeyError("Document is missing _id or has invalid type")

    # Map fields and construct the model; Pydantic will validate datetimes
    payload = {
        "id": id_str,
        "title": doc.get("title"),
        "content": doc.get("content"),
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),
    }
    try:
        return NoteOut(**payload)
    except ValidationError as e:
        # Enrich error with context to aid debugging
        raise ValidationError.from_exception_data("NoteOut", e.errors())  # type: ignore[call-arg]


# PUBLIC_INTERFACE
def note_in_to_mongo_doc(note: NoteIn) -> Dict[str, Any]:
    """
    Convert a NoteIn payload to a MongoDB insertable document.
    Adds createdAt and updatedAt timestamps.
    """
    now = datetime.utcnow()
    return {
        "title": note.title,
        "content": note.content,
        "createdAt": now,
        "updatedAt": now,
    }


# PUBLIC_INTERFACE
def apply_note_update(existing_doc: Dict[str, Any], update: NoteUpdate) -> Dict[str, Any]:
    """
    Apply a NoteUpdate payload to an existing MongoDB document and update the updatedAt timestamp.
    Does not modify createdAt and _id.
    """
    new_doc = dict(existing_doc)
    if update.title is not None:
        new_doc["title"] = update.title
    if update.content is not None:
        new_doc["content"] = update.content
    new_doc["updatedAt"] = datetime.utcnow()
    return new_doc
