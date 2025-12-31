from typing import Optional
from pydantic import BaseModel

# A single column in a table
class Attribute(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False

# A table
class Entity(BaseModel):
    name: str
    attributes: list[Attribute]

# A relationship between two tables
class Relationship(BaseModel):
    name: str
    from_entity: str
    to_entity: str
    type: str  # "one-to-one", "one-to-many", "many-to-many"

# The full schema
class Schema(BaseModel):
    schema_name: str
    entities: list[Entity]
    relationships: list[Relationship]