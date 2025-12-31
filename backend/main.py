from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from handlers import (
    handle_propose_schema,
    handle_ask_clarification,
    handle_modify_schema,
    handle_finalize_schema,
    get_current_schema,
    reset_schema
)
from diagram import schema_to_mermaid
from diagram_html import schema_to_interactive_html

load_dotenv()

app = FastAPI(title="SchemaForge API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini setup
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are SchemaForge, an expert database architect assistant. Your job is to help users design database schemas through conversation.

## How you work:
1. Listen to the user's requirements
2. Ask clarifying questions if requirements are ambiguous (use ask_clarification function)
3. Propose a schema when you have enough information (use propose_schema function)
4. Refine the schema based on feedback (use modify_schema function)
5. Finalize when the user is satisfied (use finalize_schema function)

## Guidelines:
- Ask 1-2 clarifying questions before proposing a schema
- When asking clarification, provide SHORT options (1-3 words each), maximum 4 options
- Use standard SQL data types: INT, VARCHAR(n), TEXT, DATE, DATETIME, BOOLEAN, DECIMAL(p,s)
- Every entity should have a primary key (usually entity_id as INT)
- Name entities in PascalCase (e.g., UserAccount, OrderItem)
- Name attributes in snake_case (e.g., created_at, first_name)

## Important:
- Always use the provided functions to interact
- Options must be SHORT like: "yes", "no", "students", "one-to-many"
"""

GEMINI_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="propose_schema",
                description="Propose a database schema based on user requirements.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "schema_name": types.Schema(type=types.Type.STRING),
                        "entities": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "name": types.Schema(type=types.Type.STRING),
                                    "attributes": types.Schema(
                                        type=types.Type.ARRAY,
                                        items=types.Schema(
                                            type=types.Type.OBJECT,
                                            properties={
                                                "name": types.Schema(type=types.Type.STRING),
                                                "type": types.Schema(type=types.Type.STRING),
                                                "primary_key": types.Schema(type=types.Type.BOOLEAN),
                                                "nullable": types.Schema(type=types.Type.BOOLEAN),
                                                "unique": types.Schema(type=types.Type.BOOLEAN)
                                            },
                                            required=["name", "type"]
                                        )
                                    )
                                },
                                required=["name", "attributes"]
                            )
                        ),
                        "relationships": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "name": types.Schema(type=types.Type.STRING),
                                    "from_entity": types.Schema(type=types.Type.STRING),
                                    "to_entity": types.Schema(type=types.Type.STRING),
                                    "type": types.Schema(
                                        type=types.Type.STRING,
                                        enum=["one-to-one", "one-to-many", "many-to-one", "many-to-many"]
                                    )
                                },
                                required=["name", "from_entity", "to_entity", "type"]
                            )
                        )
                    },
                    required=["schema_name", "entities", "relationships"]
                )
            ),
            types.FunctionDeclaration(
                name="ask_clarification",
                description="Ask user a clarifying question.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "question": types.Schema(type=types.Type.STRING),
                        "options": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))
                    },
                    required=["question"]
                )
            ),
            types.FunctionDeclaration(
                name="modify_schema",
                description="Modify the current schema.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": types.Schema(
                            type=types.Type.STRING,
                            enum=["add_entity", "remove_entity", "add_attribute", "remove_attribute", "add_relationship", "remove_relationship"]
                        ),
                        "target_entity": types.Schema(type=types.Type.STRING),
                        "data": types.Schema(type=types.Type.OBJECT)
                    },
                    required=["action", "data"]
                )
            ),
            types.FunctionDeclaration(
                name="finalize_schema",
                description="Mark schema as complete.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "confirmation_message": types.Schema(type=types.Type.STRING)
                    },
                    required=["confirmation_message"]
                )
            )
        ]
    )
]

# Store conversation history per session (simple in-memory for now)
conversations = {}


def process_tool_call(tool_name: str, tool_args: dict) -> dict:
    if tool_name == "propose_schema":
        return handle_propose_schema(tool_args)
    elif tool_name == "ask_clarification":
        return handle_ask_clarification(tool_args)
    elif tool_name == "modify_schema":
        return handle_modify_schema(tool_args)
    elif tool_name == "finalize_schema":
        return handle_finalize_schema(tool_args)
    return {"error": f"Unknown tool: {tool_name}"}


def clean_options(options: list) -> list:
    if not options:
        return []
    cleaned = []
    for opt in options:
        if not isinstance(opt, str):
            continue
        opt = opt.strip()
        if not opt or len(opt) > 30:
            continue
        if opt.lower() in [o.lower() for o in cleaned]:
            continue
        cleaned.append(opt)
    return cleaned[:5]


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    options: list[str] = []
    is_schema_proposed: bool = False
    schema_data: Optional[dict] = None
    diagram_html: Optional[str] = None
    mermaid_code: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id
    
    if session_id not in conversations:
        conversations[session_id] = []
    
    history = conversations[session_id]
    history.append(types.Content(role="user", parts=[types.Part.from_text(text=request.message)]))
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=GEMINI_TOOLS
            )
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    func_call = part.function_call
                    tool_name = func_call.name
                    tool_args = dict(func_call.args)
                    
                    result = process_tool_call(tool_name, tool_args)
                    history.append(types.Content(role="model", parts=[part]))
                    
                    # Get current schema if exists
                    schema = get_current_schema()
                    schema_data = schema.model_dump() if schema else None
                    diagram_html = schema_to_interactive_html() if schema else None
                    mermaid_code = schema_to_mermaid() if schema else None
                    
                    if tool_name == "ask_clarification":
                        return ChatResponse(
                            response=result.get("question", "Could you provide more details?"),
                            options=clean_options(result.get("options", [])),
                            schema_data=schema_data,
                            diagram_html=diagram_html,
                            mermaid_code=mermaid_code
                        )
                    
                    elif tool_name == "propose_schema":
                        if result.get("success"):
                            schema_info = result.get("schema", {})
                            entities = schema_info.get("entities", [])
                            relationships = schema_info.get("relationships", [])
                            
                            response_text = f"✅ Created schema: {schema_info.get('schema_name', 'Unnamed')}\n\n"
                            response_text += "📦 Entities:\n"
                            for entity in entities:
                                attrs = ", ".join(a["name"] for a in entity["attributes"])
                                response_text += f"  • {entity['name']}: {attrs}\n"
                            
                            if relationships:
                                response_text += "\n🔗 Relationships:\n"
                                for rel in relationships:
                                    response_text += f"  • {rel['from_entity']} → {rel['to_entity']} ({rel['type']})\n"
                            
                            return ChatResponse(
                                response=response_text,
                                options=["Modify", "Finalize"],
                                is_schema_proposed=True,
                                schema_data=schema_data,
                                diagram_html=diagram_html,
                                mermaid_code=mermaid_code
                            )
                        else:
                            return ChatResponse(response=f"❌ Error: {result.get('error')}")
                    
                    elif tool_name == "modify_schema":
                        if result.get("success"):
                            return ChatResponse(
                                response=f"✅ {result.get('message', 'Schema modified.')}",
                                schema_data=schema_data,
                                diagram_html=diagram_html,
                                mermaid_code=mermaid_code
                            )
                        return ChatResponse(response=f"❌ Error: {result.get('error')}")
                    
                    elif tool_name == "finalize_schema":
                        if result.get("success"):
                            return ChatResponse(
                                response=f"✅ Schema finalized!\n\n{result.get('message', '')}",
                                schema_data=schema_data,
                                diagram_html=diagram_html,
                                mermaid_code=mermaid_code
                            )
                        return ChatResponse(response=f"❌ Error: {result.get('error')}")
                
                elif part.text:
                    history.append(types.Content(role="model", parts=[part]))
                    return ChatResponse(response=part.text)
        
        return ChatResponse(response="How can I help you design your database?")
    
    except Exception as e:
        if history and history[-1].role == "user":
            history.pop()
        return ChatResponse(response=f"Sorry, error: {str(e)[:100]}")


@app.post("/reset")
async def reset_conversation(session_id: str = "default"):
    if session_id in conversations:
        conversations[session_id] = []
    reset_schema()
    return {"status": "ok"}


@app.get("/schema")
async def get_schema():
    schema = get_current_schema()
    if schema:
        return {
            "schema_data": schema.model_dump(),
            "diagram_html": schema_to_interactive_html(),
            "mermaid_code": schema_to_mermaid()
        }
    return {"schema_data": None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
