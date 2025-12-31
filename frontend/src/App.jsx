import { useState, useRef, useEffect } from 'react'
import { 
  RefreshCw, 
  Trash2, 
  Download, 
  FileJson, 
  PanelRightClose, 
  PanelRight,
  MessageSquare, 
  Database, 
  Send,
  LayoutGrid
} from 'lucide-react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Welcome to Archetict!\n\nI help you design database schemas through conversation.\n\nTell me what system you want to build:\n• A school management system\n• An e-commerce database\n• A library management system'
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
      content: '👋 Welcome to Architect!\n\nI help you design database schemas through conversation.\n\nTell me what system you want to build:\n• A school management system\n• An e-commerce database\n• A library management system'
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
            <Database size={24} color="#ffffff" strokeWidth={2} />
          </div>
          <span className="logo-text">Architect</span>
        </div>
        <div className="header-actions">
          <button onClick={resetChat} title="Reset All">
            <RefreshCw size={20} color="#a0a0b0" strokeWidth={2} />
          </button>
          <button onClick={clearChat} title="Clear Chat">
            <Trash2 size={20} color="#a0a0b0" strokeWidth={2} />
          </button>
          <button onClick={downloadHtml} title="Download HTML" disabled={!diagramHtml}>
            <Download size={20} color={diagramHtml ? "#a0a0b0" : "#444"} strokeWidth={2} />
          </button>
          <button onClick={downloadJson} title="Download JSON" disabled={!schemaData}>
            <FileJson size={20} color={schemaData ? "#a0a0b0" : "#444"} strokeWidth={2} />
          </button>
          <button 
            onClick={() => setShowDiagram(!showDiagram)} 
            title="Toggle Diagram" 
            className={showDiagram ? 'active' : ''}
          >
            {showDiagram 
              ? <PanelRightClose size={20} color="#ff6b2c" strokeWidth={2} /> 
              : <PanelRight size={20} color="#a0a0b0" strokeWidth={2} />
            }
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="panel-header">
            <div className="icon">
              <MessageSquare size={18} color="#ff6b2c" strokeWidth={2} />
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
              <Send size={20} color="#ffffff" strokeWidth={2} />
            </button>
          </div>
        </div>

        {/* Diagram Panel */}
        {showDiagram && (
          <div className="diagram-panel">
            <div className="panel-header">
              <div className="icon">
                <LayoutGrid size={18} color="#ff6b2c" strokeWidth={2} />
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
                  <LayoutGrid size={64} color="#6a6a7a" strokeWidth={1} />
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