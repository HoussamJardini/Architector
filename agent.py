import os
import json
from dotenv import load_dotenv
from groq import Groq
from tools import TOOLS
from handlers import (
    handle_propose_schema,
    handle_ask_clarification,
    handle_modify_schema,
    handle_finalize_schema,
    get_current_schema,
    reset_schema
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are SchemaForge, an expert database architect assistant. Your job is to help users design database schemas through conversation.

## How you work:
1. Listen to the user's requirements
2. Ask clarifying questions if requirements are ambiguous (use ask_clarification tool)
3. Propose a schema when you have enough information (use propose_schema tool)
4. Refine the schema based on feedback (use modify_schema tool)
5. Finalize when the user is satisfied (use finalize_schema tool)

## Guidelines:
- Always ask at least 1-2 clarifying questions before proposing a schema
- Consider: cardinality (one-to-one, one-to-many, many-to-many), nullable fields, unique constraints
- Use standard SQL data types: INT, VARCHAR(n), TEXT, DATE, DATETIME, BOOLEAN, DECIMAL(p,s)
- Every entity should have a primary key (usually entity_id as INT)
- Name entities in PascalCase (e.g., UserAccount, OrderItem)
- Name attributes in snake_case (e.g., created_at, first_name)

## Important:
- Do NOT output raw JSON to the user
- Always use the tools to create/modify schemas
- Be conversational and helpful
- When you propose or modify a schema, briefly explain what you created and why
"""

# Conversation history
messages = []


def process_tool_call(tool_name: str, tool_args: dict) -> str:
    """Execute a tool and return the result"""
    
    if tool_name == "propose_schema":
        result = handle_propose_schema(tool_args)
    elif tool_name == "ask_clarification":
        result = handle_ask_clarification(tool_args)
    elif tool_name == "modify_schema":
        result = handle_modify_schema(tool_args)
    elif tool_name == "finalize_schema":
        result = handle_finalize_schema(tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return json.dumps(result)

def chat(user_input: str) -> str:
    """Process user input and return agent response"""
    global messages
    
    # Add user message to history
    messages.append({"role": "user", "content": user_input})
    
    # Call the LLM
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    assistant_message = response.choices[0].message
    
    # Check if LLM wants to use a tool
    if assistant_message.tool_calls:
        tool_call = assistant_message.tool_calls[0]  # Handle first tool call
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        print(f"\n🔧 Using tool: {tool_name}")
        
        result = process_tool_call(tool_name, tool_args)
        result_dict = json.loads(result)
        
        # Handle each tool type directly
        if tool_name == "ask_clarification":
            # Just return the question to the user
            question = result_dict.get("question", "Could you provide more details?")
            options = result_dict.get("options", [])
            
            response_text = question
            if options:
                response_text += "\n\nOptions:\n" + "\n".join(f"  - {opt}" for opt in options)
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text
        
        elif tool_name == "propose_schema":
            # Show what was created
            if result_dict.get("success"):
                schema = result_dict.get("schema", {})
                entities = schema.get("entities", [])
                relationships = schema.get("relationships", [])
                
                response_text = f"✅ Created schema '{schema.get('schema_name', 'Unnamed')}'\n\n"
                response_text += "📦 Entities:\n"
                for entity in entities:
                    attrs = ", ".join(a["name"] for a in entity["attributes"])
                    response_text += f"  • {entity['name']}: {attrs}\n"
                
                if relationships:
                    response_text += "\n🔗 Relationships:\n"
                    for rel in relationships:
                        response_text += f"  • {rel['from_entity']} → {rel['to_entity']} ({rel['type']})\n"
                
                response_text += "\nWould you like to modify anything?"
            else:
                response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text
        
        elif tool_name == "modify_schema":
            if result_dict.get("success"):
                response_text = f"✅ {result_dict.get('message', 'Schema modified.')}"
            else:
                response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text
        
        elif tool_name == "finalize_schema":
            if result_dict.get("success"):
                response_text = f"✅ Schema finalized!\n\n{result_dict.get('message', '')}"
            else:
                response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text
    
    # No tool call, just return the text response
    content = assistant_message.content or "How can I help you design your database?"
    messages.append({"role": "assistant", "content": content})
    return content

def reset_conversation():
    """Start a fresh conversation"""
    global messages
    messages = []
    reset_schema()


# Simple CLI for testing
if __name__ == "__main__":
    print("=" * 50)
    print("SchemaForge - Database Schema Designer")
    print("Type 'quit' to exit, 'reset' to start over")
    print("=" * 50)
    print()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        elif user_input.lower() == 'reset':
            reset_conversation()
            print("Conversation reset. Start fresh!")
            continue
        elif not user_input:
            continue
        
        response = chat(user_input)
        print(f"\nSchemaForge: {response}\n")
