import { useState } from "react";
import { processQuery } from "./api";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);

  const handleSend = async () => {
    if (!input) return;
    const response = await processQuery(input);
    setMessages([...messages, { role: "user", text: input }, { role: "agent", text: response }]);
    setInput("");
  };

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h2 className="text-xl font-bold mb-2">Chat with RAG Agent</h2>
      <div className="border rounded p-2 h-64 overflow-y-scroll bg-gray-50 mb-2">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <p><b>{m.role}:</b> {m.text}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded p-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
        />
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
}
