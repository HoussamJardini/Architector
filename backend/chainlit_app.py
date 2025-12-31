import chainlit as cl
import json
import re
import os
import asyncio
import base64
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

# Configure Gemini client
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

# Define tools for Gemini
GEMINI_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="propose_schema",
                description="Propose a database schema based on user requirements. Use when you have enough information.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "schema_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name for the schema (e.g., 'SchoolDB')"
                        ),
                        "entities": types.Schema(
                            type=types.Type.ARRAY,
                            description="List of entities (tables)",
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
                description="Ask user a clarifying question when requirements are unclear.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "question": types.Schema(
                            type=types.Type.STRING,
                            description="Question to ask"
                        ),
                        "options": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(type=types.Type.STRING),
                            description="Short options (1-3 words each, max 4)"
                        )
                    },
                    required=["question"]
                )
            ),
            types.FunctionDeclaration(
                name="modify_schema",
                description="Modify the current schema based on user feedback.",
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
                description="Mark schema as complete when user is satisfied.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "confirmation_message": types.Schema(
                            type=types.Type.STRING,
                            description="Brief summary of final schema"
                        )
                    },
                    required=["confirmation_message"]
                )
            )
        ]
    )
]


def process_tool_call(tool_name: str, tool_args: dict) -> str:
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


def clean_options(options: list) -> list:
    if not options:
        return []
    
    cleaned = []
    for opt in options:
        if not isinstance(opt, str):
            continue
        opt = opt.strip()
        if not opt:
            continue
        if len(opt) > 30:
            continue
        if opt.count(' ') > 4 and any(p in opt for p in ['.', '?', '!']):
            continue
        if opt.lower() in [o.lower() for o in cleaned]:
            continue
        cleaned.append(opt)
    
    return cleaned[:5]


async def get_response(user_input: str, history: list) -> tuple[str, list, bool]:
    """Get response from Gemini"""
    options = []
    is_schema_proposed = False
    
    # Add user message to history
    history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=GEMINI_TOOLS
            )
        )
        
        # Check response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                # Check for function call
                if part.function_call:
                    func_call = part.function_call
                    tool_name = func_call.name
                    tool_args = dict(func_call.args)
                    
                    print(f"🔧 Tool called: {tool_name}")
                    
                    result = process_tool_call(tool_name, tool_args)
                    result_dict = json.loads(result)
                    
                    # Add assistant response to history
                    history.append(types.Content(role="model", parts=[part]))
                    
                    if tool_name == "ask_clarification":
                        question = result_dict.get("question", "Could you provide more details?")
                        raw_options = result_dict.get("options", [])
                        options = clean_options(raw_options)
                        return question, options, False
                    
                    elif tool_name == "propose_schema":
                        if result_dict.get("success"):
                            schema = result_dict.get("schema", {})
                            entities = schema.get("entities", [])
                            relationships = schema.get("relationships", [])
                            
                            response_text = f"✅ Created schema **{schema.get('schema_name', 'Unnamed')}**\n\n"
                            response_text += "**Entities:**\n"
                            for entity in entities:
                                attrs = ", ".join(a["name"] for a in entity["attributes"])
                                response_text += f"- {entity['name']}: {attrs}\n"
                            
                            if relationships:
                                response_text += "\n**Relationships:**\n"
                                for rel in relationships:
                                    response_text += f"- {rel['from_entity']} → {rel['to_entity']} ({rel['type']})\n"
                            
                            response_text += "\nWould you like to modify anything?"
                            options = ["Modify", "Finalize"]
                            is_schema_proposed = True
                        else:
                            response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
                        
                        return response_text, options, is_schema_proposed
                    
                    elif tool_name == "modify_schema":
                        if result_dict.get("success"):
                            response_text = f"✅ {result_dict.get('message', 'Schema modified.')}"
                        else:
                            response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
                        return response_text, [], False
                    
                    elif tool_name == "finalize_schema":
                        if result_dict.get("success"):
                            response_text = f"✅ Schema finalized!\n\n{result_dict.get('message', '')}"
                        else:
                            response_text = f"❌ Error: {result_dict.get('error', 'Unknown error')}"
                        return response_text, [], False
                
                # Regular text response
                elif part.text:
                    history.append(types.Content(role="model", parts=[part]))
                    return part.text, [], False
        
        return "How can I help you design your database?", [], False
        
    except Exception as e:
        error_str = str(e)
        print(f"Gemini error: {error_str}")
        
        # Remove failed message from history
        if history and history[-1].role == "user":
            history.pop()
        
        if "429" in error_str or "quota" in error_str.lower():
            return "⏳ Rate limit reached. Please wait a moment and try again.", [], False
        
        return f"Sorry, I encountered an error: {str(e)[:100]}", [], False


async def show_schema_diagram():
    """Show the current schema diagram embedded"""
    schema = get_current_schema()
    if schema:
        html_content = schema_to_interactive_html()
        mermaid_code = schema_to_mermaid()
        
        # Save HTML temporarily and create data URL
        html_base64 = base64.b64encode(html_content.encode()).decode()
        data_url = f"data:text/html;base64,{html_base64}"
        
        # Create an embedded viewer message
        await cl.Message(
            content=f"📊 **Schema Diagram**\n\n[🔗 Open Interactive Diagram]({data_url})\n\n**Preview:**\n```mermaid\n{mermaid_code}\n```"
        ).send()
        
        # Also provide download
        html_file = cl.File(
            name=f"{schema.schema_name}_diagram.html",
            content=html_content.encode('utf-8'),
            display="inline"
        )
        await cl.Message(
            content="📥 Or download:",
            elements=[html_file]
        ).send()

async def show_final_schema():
    """Show final schema with embedded diagram and downloads"""
    schema = get_current_schema()
    if schema:
        html_content = schema_to_interactive_html()
        schema_json = schema.model_dump_json(indent=2)
        mermaid_code = schema_to_mermaid()
        
        # Create data URL for diagram
        html_base64 = base64.b64encode(html_content.encode()).decode()
        data_url = f"data:text/html;base64,{html_base64}"
        
        await cl.Message(
            content=f"📊 **Your Schema is Ready!**\n\n[🔗 Open Interactive Diagram]({data_url})"
        ).send()
        
        # Download files
        html_file = cl.File(
            name=f"{schema.schema_name}_diagram.html",
            content=html_content.encode('utf-8'),
            display="inline"
        )
        json_file = cl.File(
            name=f"{schema.schema_name}.json",
            content=schema_json.encode('utf-8'),
            display="inline"
        )
        
        await cl.Message(
            content="📥 **Downloads:**",
            elements=[html_file, json_file]
        ).send()
        
        await cl.Message(
            content=f"**Diagram Preview:**\n```mermaid\n{mermaid_code}\n```"
        ).send()

async def ask_user_choice(options: list) -> str:
    if not options:
        return None
    
    actions = []
    for i, opt in enumerate(options):
        actions.append(
            cl.Action(
                name=f"option_{i}",
                payload={"value": opt},
                label=opt
            )
        )
    
    try:
        res = await cl.AskActionMessage(
            content="**Select an option:**",
            actions=actions,
            timeout=300
        ).send()
        
        if res:
            return res.get("payload", {}).get("value", None)
    except Exception as e:
        print(f"Error: {e}")
    
    return None


@cl.on_chat_start
async def start():
    # Initialize empty history
    cl.user_session.set("history", [])
    reset_schema()
    
    await cl.Message(
        content="👋 Welcome to **SchemaForge**!\n\nI'll help you design database schemas through conversation.\n\n**Just tell me what system you want to build**, for example:\n- \"A system for managing a school\"\n- \"An e-commerce database\"\n- \"A library management system\""
    ).send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    
    msg = cl.Message(content="🔄 Thinking...")
    await msg.send()
    
    response_text, options, is_schema_proposed = await get_response(message.content, history)
    
    msg.content = response_text
    await msg.update()
    
    schema = get_current_schema()
    if schema:
        await show_schema_diagram()
    
    while options:
        choice = await ask_user_choice(options)
        
        if choice is None:
            await cl.Message(content="💡 You can also type your answer above.").send()
            break
        
        if is_schema_proposed:
            if choice.lower() == "modify":
                await cl.Message(
                    content="What would you like to modify?\n\n- Add or remove an entity\n- Add or remove attributes\n- Change a relationship"
                ).send()
                break
            
            elif choice.lower() == "finalize":
                msg = cl.Message(content="🔄 Finalizing your schema...")
                await msg.send()
                
                response_text, options, is_schema_proposed = await get_response("finalize the schema", history)
                
                msg.content = response_text
                await msg.update()
                
                await show_final_schema()
                options = []
                break
        
        msg = cl.Message(content="🔄 Processing...")
        await msg.send()
        
        response_text, options, is_schema_proposed = await get_response(choice, history)
        
        msg.content = response_text
        await msg.update()
        
        if get_current_schema():
            await show_schema_diagram()
