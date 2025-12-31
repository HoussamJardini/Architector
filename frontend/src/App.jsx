import { useState, useRef, useEffect } from 'react'
import './App.css'

// Icon components
const IconRefresh = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
    <path d="M3 3v5h5"/>
  </svg>
)

const IconTrash = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    <line x1="10" y1="11" x2="10" y2="17"/>
    <line x1="14" y1="11" x2="14" y2="17"/>
  </svg>
)

const IconDownload = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)

const IconCode = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 18 22 12 16 6"/>
    <polyline points="8 6 2 12 8 18"/>
  </svg>
)

const IconSidebar = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <line x1="12" y1="3" x2="12" y2="21"/>
  </svg>
)

const IconChat = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
)

const IconSchema = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="3" y="14" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/>
    <path d="M10 6.5h4M6.5 10v4M17.5 10v4M10 17.5h4"/>
  </svg>
)

const IconSend = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
)

const IconDatabase = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3"/>
    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
  </svg>
)

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Welcome to SchemaForge!\n\nI help you design database schemas through conversation.\n\nTell me what system you want to build:\n• A school management system\n• An e-commerce database\n• A library management system'
    }
  ])
  const [input, setInput] = useState('')
  const [options, setOptions] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [diagramHtml, setDiagramHtml] = useState(null)
  const [schemaData, setSchemaData] = useState(null)
  const [showDiagram, setShowDiagram] = useState(true)
  
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setOptions([])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })
      
      const data = await response.json()
      
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      setOptions(data.options || [])
      
      if (data.diagram_html) {
        setDiagramHtml(data.diagram_html)
      }
      if (data.schema_data) {
        setSchemaData(data.schema_data)
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Error connecting to server. Make sure the backend is running.' }])
    }
    
    setIsLoading(false)
    inputRef.current?.focus()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleOptionClick = (option) => {
    if (option.toLowerCase() === 'modify') {
      setMessages(prev => [...prev, 
        { role: 'user', content: option },
        { role: 'assistant', content: 'What would you like to modify?\n\n• Add or remove an entity\n• Add or remove attributes\n• Change a relationship' }
      ])
      setOptions([])
    } else {
      sendMessage(option)
    }
  }

  const resetChat = async () => {
    try {
      await fetch('http://localhost:8000/reset', { method: 'POST' })
    } catch (e) {}
    
    setMessages([{
      role: 'assistant',
      content: '👋 Welcome to SchemaForge!\n\nI help you design database schemas through conversation.\n\nTell me what system you want to build:\n• A school management system\n• An e-commerce database\n• A library management system'
    }])
    setOptions([])
    setDiagramHtml(null)
    setSchemaData(null)
  }

  const clearChat = () => {
    setMessages([{
      role: 'assistant',
      content: '💬 Chat cleared. Your schema is still preserved.\n\nWhat else would you like to do?'
    }])
    setOptions([])
  }

  const downloadHtml = () => {
    if (!diagramHtml) return
    const blob = new Blob([diagramHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${schemaData?.schema_name || 'schema'}_diagram.html`
    a.click()
  }

  const downloadJson = () => {
    if (!schemaData) return
    const blob = new Blob([JSON.stringify(schemaData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${schemaData?.schema_name || 'schema'}.json`
    a.click()
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <div className="logo-icon">
            <IconDatabase />
          </div>
          <span className="logo-text">SchemaForge</span>
        </div>
        <div className="header-actions">
          <button onClick={resetChat} title="Reset All">
            <IconRefresh />
          </button>
          <button onClick={clearChat} title="Clear Chat">
            <IconTrash />
          </button>
          <button onClick={downloadHtml} title="Download HTML" disabled={!diagramHtml}>
            <IconDownload />
          </button>
          <button onClick={downloadJson} title="Download JSON" disabled={!schemaData}>
            <IconCode />
          </button>
          <button onClick={() => setShowDiagram(!showDiagram)} title="Toggle Diagram" className={showDiagram ? 'active' : ''}>
            <IconSidebar />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="panel-header">
            <div className="icon">
              <IconChat />
            </div>
            <span>Chat</span>
          </div>
          
          <div className="messages">
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.content.split('\n').map((line, j) => (
                    <span key={j}>{line}<br/></span>
                  ))}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={chatEndRef} />
          </div>

          {/* Options */}
          {options.length > 0 && (
            <div className="options">
              {options.map((opt, i) => (
                <button key={i} onClick={() => handleOptionClick(opt)} className="option-btn">
                  {opt}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="input-container">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe your database..."
              disabled={isLoading}
            />
            <button onClick={() => sendMessage(input)} disabled={isLoading || !input.trim()} className="send-btn">
              <IconSend />
            </button>
          </div>
        </div>

        {/* Diagram Panel */}
        {showDiagram && (
          <div className="diagram-panel">
            <div className="panel-header">
              <div className="icon">
                <IconSchema />
              </div>
              <span>Schema Diagram</span>
            </div>
            
            <div className="diagram-content">
              {diagramHtml ? (
                <iframe
                  srcDoc={diagramHtml}
                  title="Schema Diagram"
                />
              ) : (
                <div className="diagram-placeholder">
                  <IconSchema />
                  <p>Your schema diagram will appear here</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App