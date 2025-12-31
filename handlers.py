import json
from models import Schema, Entity, Attribute, Relationship

# This will hold the current schema during conversation
current_schema = None


def handle_propose_schema(args: dict) -> dict:
    """Create a new schema from LLM output"""
    global current_schema
    
    try:
        # Build entities
        entities = []
        for e in args["entities"]:
            attributes = [
                Attribute(
                    name=a["name"],
                    type=a["type"],
                    primary_key=a.get("primary_key", False),
                    nullable=a.get("nullable", True),
                    unique=a.get("unique", False)
                )
                for a in e["attributes"]
            ]
            entities.append(Entity(name=e["name"], attributes=attributes))
        
        # Build relationships
        relationships = [
            Relationship(
                name=r["name"],
                from_entity=r["from_entity"],
                to_entity=r["to_entity"],
                type=r["type"]
            )
            for r in args.get("relationships", [])
        ]
        
        # Create schema
        current_schema = Schema(
            schema_name=args["schema_name"],
            entities=entities,
            relationships=relationships
        )
        
        return {
            "success": True,
            "message": f"Schema '{args['schema_name']}' created with {len(entities)} entities and {len(relationships)} relationships.",
            "schema": current_schema.model_dump()
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_ask_clarification(args: dict) -> dict:
    """Handle clarification question"""
    return {
        "success": True,
        "question": args["question"],
        "options": args.get("options", [])
    }


def handle_modify_schema(args: dict) -> dict:
    """Modify the current schema"""
    global current_schema
    
    if current_schema is None:
        return {"success": False, "error": "No schema exists yet. Propose a schema first."}
    
    action = args["action"]
    data = args["data"]
    target_entity = args.get("target_entity")
    
    try:
        if action == "add_entity":
            attributes = [
                Attribute(
                    name=a["name"],
                    type=a["type"],
                    primary_key=a.get("primary_key", False),
                    nullable=a.get("nullable", True),
                    unique=a.get("unique", False)
                )
                for a in data["attributes"]
            ]
            new_entity = Entity(name=data["name"], attributes=attributes)
            current_schema.entities.append(new_entity)
            return {"success": True, "message": f"Added entity '{data['name']}'"}
        
        elif action == "remove_entity":
            entity_name = data["name"]
            current_schema.entities = [e for e in current_schema.entities if e.name != entity_name]
            # Also remove relationships involving this entity
            current_schema.relationships = [
                r for r in current_schema.relationships 
                if r.from_entity != entity_name and r.to_entity != entity_name
            ]
            return {"success": True, "message": f"Removed entity '{entity_name}'"}
        
        elif action == "add_attribute":
            for entity in current_schema.entities:
                if entity.name == target_entity:
                    new_attr = Attribute(
                        name=data["name"],
                        type=data["type"],
                        primary_key=data.get("primary_key", False),
                        nullable=data.get("nullable", True),
                        unique=data.get("unique", False)
                    )
                    entity.attributes.append(new_attr)
                    return {"success": True, "message": f"Added attribute '{data['name']}' to '{target_entity}'"}
            return {"success": False, "error": f"Entity '{target_entity}' not found"}
        
        elif action == "remove_attribute":
            for entity in current_schema.entities:
                if entity.name == target_entity:
                    entity.attributes = [a for a in entity.attributes if a.name != data["name"]]
                    return {"success": True, "message": f"Removed attribute '{data['name']}' from '{target_entity}'"}
            return {"success": False, "error": f"Entity '{target_entity}' not found"}
        
        elif action == "add_relationship":
            new_rel = Relationship(
                name=data["name"],
                from_entity=data["from_entity"],
                to_entity=data["to_entity"],
                type=data["type"]
            )
            current_schema.relationships.append(new_rel)
            return {"success": True, "message": f"Added relationship '{data['name']}'"}
        
        elif action == "remove_relationship":
            rel_name = data["name"]
            current_schema.relationships = [r for r in current_schema.relationships if r.name != rel_name]
            return {"success": True, "message": f"Removed relationship '{rel_name}'"}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_finalize_schema(args: dict) -> dict:
    """Finalize the schema"""
    global current_schema
    
    if current_schema is None:
        return {"success": False, "error": "No schema to finalize"}
    
    return {
        "success": True,
        "message": args["confirmation_message"],
        "final_schema": current_schema.model_dump()
    }


def get_current_schema():
    """Return the current schema"""
    return current_schema


def reset_schema():
    """Clear the current schema"""
    global current_schema
    current_schema = None