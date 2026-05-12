import React, { useState, useEffect, useRef } from 'react';

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    { role: 'ai', content: "Hi! I'm Trackify AI. Ask me anything about your team's time logs, projects, or productivity.", time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showChips, setShowChips] = useState(true);
  const [sessionId, setSessionId] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const send = async (text) => {
    const val = text.trim();
    if (!val) return;

    setShowChips(false);
    setInput('');
    
    const newMsg = { role: 'user', content: val, time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) };
    const newMessages = [...messages, newMsg];
    setMessages(newMessages);
    setIsTyping(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
          session_id: sessionId
        })
      });
      const data = await res.json();
      
      setMessages([...newMessages, { role: 'ai', content: data.reply, time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) }]);
    } catch (err) {
      console.error(err);
      setMessages([...newMessages, { role: 'ai', content: "Sorry, I couldn't connect to the server.", time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      send(input);
    }
  };

  const clearChat = async () => {
    setMessages([{ role: 'ai', content: 'Chat cleared. Ask me anything about your team.', time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) }]);
    setShowChips(true);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_URL}/api/v1/conversations/${sessionId}/clear`, { method: 'POST' });
    } catch(err) {}
  };

  return (
    <div className="flex h-[560px] rounded-xl overflow-hidden border border-gray-200 bg-gray-50 text-gray-900 font-sans">
      {/* Sidebar */}
      <div className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-5 flex items-center gap-2.5 border-b border-gray-200">
          <div className="bg-blue-600 text-white w-8 h-8 rounded-lg flex items-center justify-center font-bold text-[15px] shrink-0">T</div>
          <span className="font-bold text-[15px]">Trackify AI</span>
        </div>
        <nav className="p-3 flex-1">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium mb-0.5 cursor-pointer transition-colors bg-blue-50 text-blue-600">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
            Chat
          </div>
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-500 mb-0.5 cursor-pointer hover:bg-gray-100 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
            Dashboard
          </div>
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-500 mb-0.5 cursor-pointer hover:bg-gray-100 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            Reports
          </div>
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-500 mb-0.5 cursor-pointer hover:bg-gray-100 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
            Projects
          </div>
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-gray-500 mb-0.5 cursor-pointer hover:bg-gray-100 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            Team
          </div>
        </nav>
        <div className="p-3 border-t border-gray-200">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
            <div className="w-7 h-7 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center text-[10px] font-bold shrink-0">MG</div>
            <span className="text-[13px] font-medium text-gray-700">Manager</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-gray-50">
        {/* Topbar */}
        <div className="h-14 bg-white border-b border-gray-200 flex items-center px-6 gap-3 shrink-0">
          <span className="font-semibold text-[15px]">Chat Assistant</span>
          <span className="text-[11px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium">Powered by Groq</span>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={clearChat} className="w-8 h-8 rounded-lg border border-gray-200 bg-white flex items-center justify-center text-gray-500 hover:bg-gray-100 transition-colors" title="Clear chat">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 md:p-6 flex flex-col gap-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-2.5 max-w-full ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5 ${msg.role === 'user' ? 'bg-gray-100 text-gray-500' : 'bg-blue-50 text-blue-600'}`}>
                {msg.role === 'user' ? 'You' : 'AI'}
              </div>
              <div className={`flex flex-col gap-1 max-w-[75%] ${msg.role === 'user' ? 'items-end' : ''}`}>
                <div 
                  className={`px-3.5 py-2.5 rounded-xl text-[13.5px] leading-relaxed ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-tr-sm' 
                      : 'bg-white border border-gray-200 rounded-tl-sm text-gray-900 shadow-sm whitespace-pre-wrap'
                  }`}
                  dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>') }}
                />
                <span className="text-[10.5px] text-gray-400">{msg.time}</span>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-2.5 max-w-full">
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5 bg-blue-50 text-blue-600">AI</div>
              <div className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl rounded-tl-sm w-fit shadow-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '0s' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}

          {showChips && (
            <div className="flex flex-wrap gap-1.5 mt-1 ml-9">
              <button onClick={() => send("Who logged most hours this week?")} className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:border-blue-600 hover:text-blue-600 hover:bg-blue-50 transition-colors whitespace-nowrap">Who logged most hours this week?</button>
              <button onClick={() => send("Show idle team members")} className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:border-blue-600 hover:text-blue-600 hover:bg-blue-50 transition-colors whitespace-nowrap">Show idle team members</button>
              <button onClick={() => send("List all projects")} className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:border-blue-600 hover:text-blue-600 hover:bg-blue-50 transition-colors whitespace-nowrap">List all projects</button>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="px-6 pt-3 pb-4 bg-gray-50 border-t border-gray-200 shrink-0">
          <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl p-2 pl-3.5 focus-within:border-blue-600 transition-colors shadow-sm">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your team..." 
              className="flex-1 border-none outline-none text-[13.5px] bg-transparent text-gray-900 placeholder-gray-400 font-sans"
            />
            <button 
              onClick={() => send(input)}
              disabled={isTyping || !input.trim()}
              className="w-8 h-8 rounded-lg bg-blue-600 disabled:bg-gray-300 text-white flex items-center justify-center shrink-0 hover:bg-blue-700 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
