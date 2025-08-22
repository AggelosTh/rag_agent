import { useState } from "react";
import ChatBox from "./ChatBox";
import DocumentManager from "./DocumentManager";

function App() {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">RAG Agent UI</h1>

      {/* Tab buttons */}
      <div className="flex gap-4 mb-6">
        <button
          className={`px-4 py-2 rounded transition ${
            activeTab === "chat"
              ? "bg-blue-600 text-white shadow-md"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
          onClick={() => setActiveTab("chat")}
        >
          💬 Chat
        </button>
        <button
          className={`px-4 py-2 rounded transition ${
            activeTab === "docs"
              ? "bg-blue-600 text-white shadow-md"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
          onClick={() => setActiveTab("docs")}
        >
          📂 Documents
        </button>
      </div>

      {/* Keep both mounted, toggle visibility */}
      <div>
        <div className={activeTab === "chat" ? "" : "hidden"}>
          <ChatBox />
        </div>
        <div className={activeTab === "docs" ? "" : "hidden"}>
          <DocumentManager />
        </div>
      </div>
    </div>
  );
}

export default App;
