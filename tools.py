# Tool definitions for the LLM
# These tell the LLM what tools exist and what parameters they need

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "propose_schema",
            "description": "Propose a database schema based on the user's requirements. Use this when you have enough information to suggest entities, attributes, and relationships.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema_name": {
                        "type": "string",
                        "description": "A name for this schema (e.g., 'LibrarySystem', 'EcommerceDB')"
                    },
                    "entities": {
                        "type": "array",
                        "description": "List of entities (tables) in the schema",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Entity name (e.g., 'Book', 'User')"
                                },
                                "attributes": {
                                    "type": "array",
                                    "description": "List of attributes (columns) for this entity",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "type": {"type": "string", "description": "SQL data type (INT, VARCHAR(255), DATE, etc.)"},
                                            "primary_key": {"type": "boolean", "default": False},
                                            "nullable": {"type": "boolean", "default": True},
                                            "unique": {"type": "boolean", "default": False}
                                        },
                                        "required": ["name", "type"]
                                    }
                                }
                            },
                            "required": ["name", "attributes"]
                        }
                    },
                    "relationships": {
                        "type": "array",
                        "description": "List of relationships between entities",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Relationship name (verb, e.g., 'has', 'belongs_to')"},
                                "from_entity": {"type": "string"},
                                "to_entity": {"type": "string"},
                                "type": {"type": "string", "enum": ["one-to-one", "one-to-many", "many-to-many", "many-to-one"]}
                            },
                            "required": ["name", "from_entity", "to_entity", "type"]
                        }
                    }
                },
                "required": ["schema_name", "entities", "relationships"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Ask the user a clarifying question when requirements are ambiguous or incomplete. Use this before proposing a schema if you need more information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the user"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of suggested answers to help the user"
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_schema",
            "description": "Modify the current schema based on user feedback. Use this when the user wants to add, remove, or change entities, attributes, or relationships.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add_entity", "remove_entity", "add_attribute", "remove_attribute", "add_relationship", "remove_relationship", "modify_entity", "modify_attribute"],
                        "description": "The type of modification to make"
                    },
                    "target_entity": {
                        "type": "string",
                        "description": "The entity to modify (for attribute changes)"
                    },
                    "data": {
                        "type": "object",
                        "description": "The data for the modification (new entity, attribute, or relationship)"
                    }
                },
                "required": ["action", "data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_schema",
            "description": "Mark the schema as complete and ready for export. Use this when the user confirms they are satisfied with the design.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_message": {
                        "type": "string",
                        "description": "A brief summary of the final schema"
                    }
                },
                "required": ["confirmation_message"]
            }
        }
    }
]