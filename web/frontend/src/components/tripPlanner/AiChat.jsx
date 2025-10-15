import React, { useState, useEffect, useRef } from 'react';

const AiChat = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hello! I'm TripCraft's AI assistant. How can I help you plan your perfect trip?",
      sender: 'ai'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (inputValue.trim()) {
      const newMessages = [
        ...messages,
        { id: Date.now(), text: inputValue, sender: 'user' }
      ];
      setMessages(newMessages);
      setInputValue('');

      setTimeout(() => {
        setMessages(prev => [
          ...prev,
          {
            id: Date.now() + 1,
            text: "That's a great question! Let me look into that for you...",
            sender: 'ai'
          }
        ]);
      }, 1000);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="ai-chat">
      <div className={`chat-window ${isOpen ? 'open' : ''}`}>
        <div className="chat-header">
          <h3 className="chat-header-title">AI Assistant</h3>
          <button onClick={() => setIsOpen(false)} className="chat-close-btn">
            <i className="fas fa-times"></i>
          </button>
        </div>
        <div className="chat-messages">
          <div className="messages-container">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`message ${msg.sender === 'user' ? 'message-user' : 'message-ai'}`}
              >
                <div className="message-bubble">
                  {msg.text}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
        </div>
        <div className="chat-input-container">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything..."
            className="chat-input"
          />
          <button onClick={handleSend} className="chat-send-btn">
            <i className="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="chat-toggle-btn"
      >
        <i className={`fas ${isOpen ? 'fa-times' : 'fa-comments'}`}></i>
      </button>
    </div>
  );
};

export default AiChat;
