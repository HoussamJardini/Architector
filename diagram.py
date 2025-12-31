from handlers import get_current_schema

# Words that conflict with Mermaid syntax
RESERVED_WORDS = ["class", "entity", "relationship"]


def safe_name(name: str) -> str:
    """Make entity names safe for Mermaid"""
    if name.lower() in RESERVED_WORDS:
        return f"{name}Entity"
    return name


def schema_to_mermaid() -> str:
    """Convert current schema to Mermaid ERD syntax"""
    
    schema = get_current_schema()
    
    if schema is None:
        return "No schema to display."
    
    lines = ["erDiagram"]
    
    # Add entities with their attributes
    for entity in schema.entities:
        entity_name = safe_name(entity.name)
        lines.append(f"    {entity_name} {{")
        for attr in entity.attributes:
            # Determine key type
            key_marker = ""
            if attr.primary_key:
                key_marker = "PK"
            elif attr.unique:
                key_marker = "UK"
            
            # Clean up type for display (remove special characters)
            display_type = attr.type.replace("(", "").replace(")", "").replace(",", "").replace(" ", "")
            
            if key_marker:
                lines.append(f"        {display_type} {attr.name} {key_marker}")
            else:
                lines.append(f"        {display_type} {attr.name}")
        lines.append("    }")
    
    lines.append("")
    
    # Add relationships
    for rel in schema.relationships:
        from_entity = safe_name(rel.from_entity)
        to_entity = safe_name(rel.to_entity)
        
        # Convert relationship type to Mermaid syntax
        if rel.type == "one-to-one":
            connector = "||--||"
        elif rel.type == "one-to-many":
            connector = "||--o{"
        elif rel.type == "many-to-one":
            connector = "}o--||"
        elif rel.type == "many-to-many":
            connector = "}o--o{"
        else:
            connector = "||--||"
        
        # Clean relationship name (no spaces)
        rel_name = rel.name.replace(" ", "_")
        
        lines.append(f"    {from_entity} {connector} {to_entity} : {rel_name}")
    
    return "\n".join(lines)


def print_diagram():
    """Print the Mermaid diagram to console"""
    print("\n" + "=" * 50)
    print("📊 MERMAID ERD DIAGRAM")
    print("=" * 50)
    print("\nCopy this to https://mermaid.live to view:\n")
    print(schema_to_mermaid())
    print("\n" + "=" * 50)