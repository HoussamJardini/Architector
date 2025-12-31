import streamlit as st
import json
import re
import os
import time
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
from diagram import schema_to_mermaid

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
- Ask 1-2 clarifying questions before proposing a schema
- Consider: cardinality (one-to-one, one-to-many, many-to-many), nullable fields, unique constraints
- Use standard SQL data types: INT, VARCHAR(n), TEXT, DATE, DATETIME, BOOLEAN, DECIMAL(p,s)
- Every entity should have a primary key (usually entity_id as INT)
- Name entities in PascalCase (e.g., UserAccount, OrderItem)
- Name attributes in snake_case (e.g., created_at, first_name)
- maeke sure there is no classes hanging aroud with no connections t other classes, connect them by eather asking the user or make the conenction based on what you understood
## IMPORTANT - Tool Usage Rules:
- Always use the provided tools to interact
- Do NOT write function calls as text
- Simply call the tools directly through the function calling mechanism
- Never output raw JSON or function syntax in your text responses
"""


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


def chat(user_input: str, messages: list) -> tuple[str, list]:
    """Process user input and return (response, options)"""
    
    messages.append({"role": "user", "content": user_input})
    options = []
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
            tool_choice="auto"
        )
    except Exception as e:
        error_str = str(e)
        
        if "failed_generation" in error_str:
            question_match = re.search(r'"question":\s*"([^"]+)"', error_str)
            options_match = re.findall(r'"options":\s*\[(.*?)\]', error_str)
            
            if question_match:
                question = question_match.group(1)
                
                if options_match:
                    options = re.findall(r'"([^"]+)"', options_match[0])
                
                messages.append({"role": "assistant", "content": question})
                return question, options
        
        messages.pop()
        return f"Sorry, I encountered an error. Please try rephrasing.", []
    
    assistant_message = response.choices[0].message
    
    if assistant_message.tool_calls:
        tool_call = assistant_message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        result = process_tool_call(tool_name, tool_args)
        result_dict = json.loads(result)
        
        if tool_name == "ask_clarification":
            question = result_dict.get("question", "Could you provide more details?")
            options = result_dict.get("options", [])
            
            messages.append({"role": "assistant", "content": question})
            return question, options
        
        elif tool_name == "propose_schema":
            if result_dict.get("success"):
                schema = result_dict.get("schema", {})
                entities = schema.get("entities", [])
                relationships = schema.get("relationships", [])
                
                response_text = f"Created schema **{schema.get('schema_name', 'Unnamed')}**\n\n"
                response_text += "**Entities:**\n"
                for entity in entities:
                    attrs = ", ".join(a["name"] for a in entity["attributes"])
                    response_text += f"• {entity['name']}: {attrs}\n"
                
                if relationships:
                    response_text += "\n**Relationships:**\n"
                    for rel in relationships:
                        response_text += f"• {rel['from_entity']} → {rel['to_entity']} ({rel['type']})\n"
                
                response_text += "\nWould you like to modify anything?"
                options = ["Yes, modify", "No, finalize"]
            else:
                response_text = f"Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text, options
        
        elif tool_name == "modify_schema":
            if result_dict.get("success"):
                response_text = result_dict.get('message', 'Schema modified.')
            else:
                response_text = f"Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text, []
        
        elif tool_name == "finalize_schema":
            if result_dict.get("success"):
                response_text = f"Schema finalized!\n\n{result_dict.get('message', '')}"
            else:
                response_text = f"Error: {result_dict.get('error', 'Unknown error')}"
            
            messages.append({"role": "assistant", "content": response_text})
            return response_text, []
    
    content = assistant_message.content or "How can I help you design your database?"
    messages.append({"role": "assistant", "content": content})
    return content, []


def send_message(message: str):
    """Send a message and update state"""
    st.session_state.chat_history.append({"role": "user", "content": message})
    st.session_state.is_loading = True
    response, options = chat(message, st.session_state.messages)
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.session_state.current_options = options
    st.session_state.is_loading = False


# ============== STREAMLIT CONFIG ==============

st.set_page_config(
    page_title="SchemaForge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============== CUSTOM CSS ==============

st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Header */
    .main-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        color: #666;
        font-size: 1.1rem;
    }
    
    /* Chat container */
    .chat-container {
        background: #fafafa;
        border-radius: 16px;
        padding: 1.5rem;
        height: 450px;
        overflow-y: auto;
        border: 1px solid #e8e8e8;
        margin-bottom: 1rem;
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
        font-size: 0.95rem;
        line-height: 1.5;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
    }
    
    .assistant-message {
        background: white;
        color: #1a1a1a;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        font-size: 0.95rem;
        line-height: 1.5;
        border: 1px solid #e8e8e8;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Options buttons */
    .stButton > button {
        background: white;
        color: #667eea;
        border: 2px solid #667eea;
        border-radius: 25px;
        padding: 8px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: #667eea;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
    }
    
    /* Diagram section */
    .diagram-section {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e8e8e8;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #667eea;
        display: inline-block;
    }
    
    /* Loading animation */
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 300px;
        color: #666;
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 300px;
        color: #999;
        text-align: center;
    }
    
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    /* Reset button */
    .reset-btn {
        margin-top: 1rem;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
    }
    
    .stDownloadButton > button:hover {
        opacity: 0.9;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
    }
    
    /* Slider */
    .stSlider > div > div {
        background: #667eea;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ============== INITIALIZE STATE ==============

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_options" not in st.session_state:
    st.session_state.current_options = []
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False

# ============== HEADER ==============

st.markdown("""
<div class="main-header">
    <h1>SchemaForge</h1>
    <p>Design database schemas through natural conversation</p>
</div>
""", unsafe_allow_html=True)

# ============== LAYOUT ==============

col1, spacer, col2 = st.columns([5, 0.5, 5])

# ============== CHAT SECTION ==============

with col1:
    st.markdown('<p class="section-header">Chat</p>', unsafe_allow_html=True)
    
    # Chat messages container
    chat_html = '<div class="chat-container">'
    
    if not st.session_state.chat_history:
        chat_html += '''
        <div class="empty-state">
            <div class="empty-state-icon">💬</div>
            <p>Start by describing the database you want to create</p>
        </div>
        '''
    else:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f'<div class="user-message">{msg["content"]}</div>'
            else:
                # Convert markdown bold to HTML
                content = msg["content"].replace("**", "<strong>").replace("**", "</strong>")
                content = content.replace("\n", "<br>")
                chat_html += f'<div class="assistant-message">{content}</div>'
    
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Options buttons
    if st.session_state.current_options:
        st.markdown("")  # Spacing
        cols = st.columns(len(st.session_state.current_options))
        for i, option in enumerate(st.session_state.current_options):
            with cols[i]:
                if st.button(option, key=f"opt_{i}", use_container_width=True):
                    st.session_state.current_options = []
                    send_message(option)
                    st.rerun()
    
    st.markdown("")  # Spacing
    
    # Input
    user_input = st.chat_input("Describe your database needs...")
    
    if user_input:
        st.session_state.current_options = []
        send_message(user_input)
        st.rerun()
    
    # Reset button
    st.markdown("")  # Spacing
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.current_options = []
        reset_schema()
        st.rerun()

# ============== DIAGRAM SECTION ==============

with col2:
    st.markdown('<p class="section-header">Schema Diagram</p>', unsafe_allow_html=True)
    
    schema = get_current_schema()
    
    if schema:
        mermaid_code = schema_to_mermaid()
        
        # Zoom slider
        zoom_level = st.slider("Zoom", min_value=50, max_value=200, value=100, step=10, format="%d%%", label_visibility="collapsed")
        
        # Mermaid diagram with loading animation
        mermaid_html = f"""
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    background: transparent;
                }}
                
                .diagram-wrapper {{
                    width: 100%;
                    height: 380px;
                    overflow: auto;
                    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
                    border-radius: 12px;
                    border: 1px solid #e0e0e0;
                }}
                
                .diagram-inner {{
                    transform: scale({zoom_level / 100});
                    transform-origin: top left;
                    padding: 24px;
                    display: inline-block;
                    min-width: 100%;
                }}
                
                .mermaid {{
                    background: transparent;
                }}
                
                .mermaid svg {{
                    max-width: none !important;
                }}
                
                /* Loading state */
                .loading {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 380px;
                }}
                
                .spinner {{
                    width: 40px;
                    height: 40px;
                    border: 3px solid #e0e0e0;
                    border-top-color: #667eea;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                }}
                
                @keyframes spin {{
                    to {{ transform: rotate(360deg); }}
                }}
                
                .loading-text {{
                    margin-top: 12px;
                    color: #666;
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    font-size: 14px;
                }}
                
                /* Fade in animation */
                .fade-in {{
                    animation: fadeIn 0.5s ease-out;
                }}
                
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(10px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
            </style>
        </head>
        <body>
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <div class="loading-text">Rendering diagram...</div>
            </div>
            
            <div class="diagram-wrapper" id="diagram" style="display: none;">
                <div class="diagram-inner">
                    <div class="mermaid fade-in">
                    {mermaid_code}
                    </div>
                </div>
            </div>
            
            <script>
                mermaid.initialize({{
                    startOnLoad: false,
                    theme: 'default',
                    securityLevel: 'loose',
                    er: {{
                        useMaxWidth: false,
                        entityPadding: 15,
                        fontSize: 14
                    }}
                }});
                
                mermaid.run().then(() => {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('diagram').style.display = 'block';
                }});
            </script>
        </body>
        </html>
        """
        
        st.components.v1.html(mermaid_html, height=420, scrolling=False)
        
        st.markdown("")  # Spacing
        
        # Mermaid code expander
        with st.expander("View Mermaid Code"):
            st.code(mermaid_code, language="text")
        
        st.markdown("")  # Spacing
        
        # Export
        st.markdown('<p class="section-header">Export</p>', unsafe_allow_html=True)
        
        schema_json = schema.model_dump_json(indent=2)
        st.download_button(
            label="Download Schema (JSON)",
            data=schema_json,
            file_name=f"{schema.schema_name}.json",
            mime="application/json",
            use_container_width=True
        )
    
    else:
        # Empty state with nice styling
        st.markdown("""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 400px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            color: #888;
            text-align: center;
        ">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.4;">📊</div>
            <p style="font-size: 1rem; max-width: 250px;">
                Your schema diagram will appear here as you design it
            </p>
        </div>
        """, unsafe_allow_html=True)
