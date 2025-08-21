import React, { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { Send } from "lucide-react";

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

const handleSend = async () => {
  if (!input.trim()) return;

  const newMessage = { text: input, sender: "user" };
  setMessages((prev) => [...prev, newMessage]);
  setInput("");

  try {
    const response = await axios.post("http://localhost:8000/process", null, {
      params: { user_input: input },
    });

    // check if backend returns { answer: "..."}
    const answer =
      response.data.answer !== undefined
        ? response.data.answer
        : response.data.response || JSON.stringify(response.data);

    const botMessage = { text: answer, sender: "bot" };
    setMessages((prev) => [...prev, botMessage]);
  } catch (error) {
    setMessages((prev) => [
      ...prev,
      { text: "⚠️ Network error. Try again.", sender: "bot" },
    ]);
  }
};

  return (
    <div className="bg-white shadow-lg rounded-2xl p-4 w-full max-w-2xl mx-auto flex flex-col h-[500px]">
      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-2">
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={`p-3 rounded-2xl max-w-[75%] ${
              msg.sender === "user"
                ? "bg-blue-500 text-white self-end ml-auto"
                : "bg-gray-200 text-gray-800 self-start"
            }`}
          >
            {msg.text}
          </motion.div>
        ))}
      </div>

      {/* Input */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="Type your message..."
        />
        <button
          onClick={handleSend}
          className="p-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
