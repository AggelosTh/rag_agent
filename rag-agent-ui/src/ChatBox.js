import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { Send, Bot, User, Loader2, FileText } from "lucide-react";

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [useSummarization, setUseSummarization] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const newMessage = { text: input, sender: "user", id: Date.now() };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post("http://localhost:8000/process", null, {
        params: { 
          user_input: input,
          use_summarization: useSummarization
        },
      });

      const answer =
        response.data.answer !== undefined
          ? response.data.answer
          : response.data.response || JSON.stringify(response.data);

      const botMessage = { 
        text: answer, 
        sender: "bot", 
        id: Date.now() + 1
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { 
          text: "Sorry, I couldn't connect to the server. Please try again.", 
          sender: "bot", 
          id: Date.now() + 1,
          isError: true 
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-4xl mx-auto flex flex-col h-[700px]">
      
      {/* Header */}
      <div className="flex items-center justify-center mb-6 pb-4 border-b-2 border-gray-200">
        <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center mr-4">
          <Bot className="w-7 h-7 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-black text-gray-800">
            Chat Assistant
          </h2>
          <p className="text-gray-600 font-semibold">Ask me anything about your documents</p>
        </div>
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto mb-6 space-y-4 px-2">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div className="w-20 h-20 bg-gradient-to-r from-purple-400 to-blue-400 rounded-full flex items-center justify-center mx-auto mb-6">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <p className="text-xl font-bold text-gray-700 mb-2">Start a conversation</p>
            <p className="text-gray-500 font-medium">I'm here to help with your documents</p>
          </div>
        )}
        
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex items-start gap-3 ${
              msg.sender === "user" ? "flex-row-reverse" : ""
            }`}
          >
            {/* Avatar */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
              msg.sender === "user"
                ? "bg-gradient-to-r from-green-500 to-emerald-500"
                : msg.isError
                ? "bg-gradient-to-r from-red-500 to-pink-500"
                : "bg-gradient-to-r from-purple-500 to-blue-500"
            }`}>
              {msg.sender === "user" ? (
                <User className="w-5 h-5 text-white" />
              ) : (
                <Bot className="w-5 h-5 text-white" />
              )}
            </div>

            {/* Message bubble */}
            <div className={`max-w-[75%] rounded-2xl px-5 py-4 ${
              msg.sender === "user"
                ? "bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg"
                : msg.isError
                ? "bg-gradient-to-r from-red-100 to-pink-100 text-red-800 border-2 border-red-300"
                : "bg-gray-100 text-gray-800 shadow-lg"
            }`}>
              <div className="font-medium leading-relaxed">
                {msg.text}
              </div>
              <div className={`text-xs mt-2 ${
                msg.sender === "user" ? "text-green-100" : "text-gray-500"
              }`}>
                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </motion.div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-gray-100 rounded-2xl px-5 py-4 shadow-lg">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-purple-500" />
                <span className="text-gray-600 font-medium">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-2xl border-2 border-gray-200">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={isLoading}
          className="flex-1 bg-transparent text-gray-800 placeholder-gray-500 focus:outline-none text-lg font-medium"
          placeholder="Type your message here..."
        />
        
        {/* Summarization Toggle */}
        <button
          onClick={() => setUseSummarization(!useSummarization)}
          className={`px-4 py-2 rounded-xl font-bold text-sm transition-all duration-200 flex items-center gap-2 ${
            useSummarization
              ? "bg-gradient-to-r from-yellow-500 to-orange-500 text-white shadow-lg"
              : "bg-gray-200 hover:bg-gray-300 text-gray-700"
          }`}
        >
          <FileText className="w-4 h-4" />
          Summarization
        </button>
        
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className={`p-3 rounded-xl transition-all duration-200 ${
            isLoading || !input.trim()
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white shadow-lg"
          }`}
        >
          {isLoading ? (
            <Loader2 className="w-6 h-6 animate-spin" />
          ) : (
            <Send className="w-6 h-6" />
          )}
        </button>
      </div>
    </div>
  );
}