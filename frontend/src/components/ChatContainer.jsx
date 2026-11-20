import React, { useState, useEffect, useCallback, useRef } from 'react';
import Icon from './Icon.jsx';
import { t } from '../ui/i18n.js';

/**
 * ChatContainer Component
 * The primary interface for interacting with the AI Agent.
 * Integrations:
 * - useAgentStream for SSE connection.
 * - ThoughtProcessTerminal for real-time reasoning trace.
 * - Sidebar/Sidebar components (managed by parent).
 * - ReasoningDashboard for L1-L5 status.
 */

export default function ChatContainer({ sidebarOpen, reasoningInfo }) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const messagesEndRef = useRef(null);

  // API URL - typically configured via env
  const API_BASE = 'http://localhost:8000';

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // SSE Handling via Fetch API (Replacement for EventSource for POST support)
  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userText = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    setLogs([]); // Clear old thought process for new task
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          session_id: 'current_session', // In real app, get from context
          mode: 'code'
        }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = { role: 'assistant', content: '' };
      setMessages(prev => [...prev, assistantMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.trim()) continue;
          const dataStr = line.replace(/^data: /, '');
          
          try {
            const event = JSON.parse(dataStr);
            
            switch (event.type) {
              case 'stream':
                assistantMessage.content += event.data;
                setMessages(prev => [...prev.slice(0, -1), { ...assistantMessage }]);
                break;
              case 'thought':
                setLogs(prev => [...prev, { type: 'thought', message: event.data, timestamp: Date.now() }]);
                break;
              case 'action':
                setLogs(prev => [...prev, { type: 'tool', message: `Executing: ${event.data.tool}`, timestamp: Date.now() }]);
                break;
              case 'observation':
                setLogs(prev => [...prev, { type: 'observation', message: event.data.output?.slice(0, 200) || 'Done', timestamp: Date.now() }]);
                break;
              case 'error':
                setLogs(prev => [...prev, { type: 'error', message: event.data, timestamp: Date.now() }]);
                break;
              case 'final':
                assistantMessage.content = event.data;
                setMessages(prev => [...prev.slice(0, -1), { ...assistantMessage }]);
                break;
            }
} catch (e) {
            // Handle raw streaming text if not JSON
            assistantMessage.content += dataStr;
            setMessages(prev => [...prev.slice(0, -1), { ...assistantMessage }]);
          }
        }
      }
    } catch (error) {
      console.error("Stream error:", error);
      setLogs(prev => [...prev, { type: 'error', message: error.message, timestamp: Date.now() }]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#050505] overflow-hidden">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-[#8B0000]/30">
        {/* Chat Header */}
        <div className="h-14 bg-[#0A0A0A] border-b border-[#8B0000]/50 flex items-center px-6 justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-[#CC0000] animate-pulse" />
            <h1 className="text-[#FF4444] font-bold tracking-widest uppercase text-xs">Neural Core Active</h1>
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-tighter">
            {isStreaming ? 'Processing...' : 'Ready'}
          </div>
        </div>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-[#333]">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-gray-700">
              <Icon name="spark" size={48} className="opacity-20 mb-4" />
              <p className="text-sm italic">Waiting for command input...</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] px-4 py-3 rounded-lg text-sm leading-relaxed shadow-xl ${
                msg.role === 'user' 
                  ? 'bg-[#CC0000] text-white rounded-br-none' 
                  : 'bg-[#1A1A1A] text-gray-200 border border-[#333] rounded-bl-none'
              }`}>
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Box */}
        <div className="p-4 bg-[#0A0A0A] border-t border-[#8B0000]/30">
          <div className="relative max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Execute instruction or request code..."
              disabled={isStreaming}
              className="w-full bg-[#151515] border border-[#333] text-white pl-4 pr-12 py-3 rounded-xl focus:outline-none focus:border-[#CC0000] transition-all disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[#CC0000] hover:text-[#FF4444] disabled:text-gray-700 transition-colors"
            >
              <Icon name="send" size={20} />
            </button>
          </div>
          <p className="text-center text-[9px] text-gray.600 mt-2">
            WormGPT Ultra Singularity | L1-L5 Adaptive Intelligence | Continuous Execution Mode
          </p>
        </div>
      </div>

      {/* Right Sidebar: Intelligence Trace */}
      <div className="w-96 bg-[#050505] flex flex-col border-l border-[#222]">
        {/* Reasoning Stats */}
        <div className="p-4 border-b border-[#222] bg-[#0A0A0A]">
          <div className="text-[10px] text-[#8B0000] font-bold uppercase mb-3">Reasoning Diagnostics</div>
          <div className="space-y-3">
             {/* Placeholder for dynamic ReasoningDashboard component */}
             <div className="text-[11px] text-gray-500">Monitoring mental entropy and planning vectors...</div>
          </div>
        </div>

        {/* Thought Process Terminal */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-3 py-2 text-[10px] text-gray-500 border-b border-[#111] bg-[#080808] font-mono uppercase tracking-widest">
            Thought Process Trace
          </div>
          <div className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-2 bg-black/50">
            {logs.length === 0 ? (
              <div className="text-gray-800 italic">Idle...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className={`flex gap-2 ${
                  log.type === 'error' ? 'text-red-500' : 
                  log.type === 'success' ? 'text-green-500' : 
                  log.type === 'tool' ? 'text-blue-400' : 'text-gray-400'
                }`}>
                  <span className="opacity-30">[{new Date(log.timestamp).toLocaleTimeString([], {hour12:false, hour:'2-digit', minute:'2-digit', second:'2-digit'})}]</span>
                  <span className="shrink-0">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}