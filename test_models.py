from models import Schema, Entity, Attribute, Relationship

# Create a sample schema
library_schema = Schema(
    schema_name="LibrarySystem",
    entities=[
        Entity(
            name="Book",
            attributes=[
                Attribute(name="book_id", type="INT", primary_key=True, nullable=False),
                Attribute(name="title", type="VARCHAR(255)", nullable=False),
                Attribute(name="isbn", type="VARCHAR(13)", unique=True)
            ]
        ),
        Entity(
            name="Author",
            attributes=[
                Attribute(name="author_id", type="INT", primary_key=True, nullable=False),
                Attribute(name="name", type="VARCHAR(100)", nullable=False)
            ]
        )
    ],
    relationships=[
        Relationship(
            name="writes",
            from_entity="Author",
            to_entity="Book",
            type="one-to-many"
        )
    ]
)

# Print as JSON to see the structure
print(library_schema.model_dump_json(indent=2))
