import { useState } from "react";
import ChatBox from "./ChatBox";
import DocumentManager from "./DocumentManager";
import { motion } from "framer-motion";
import { MessageSquare, Folder } from "lucide-react";

function App() {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white flex flex-col items-center p-8">
      {/* Header */}
      <motion.h1
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-4xl font-extrabold tracking-tight mb-8"
      >
        ⚡ RAG Agent Dashboard
      </motion.h1>

      {/* Tabs */}
      <motion.div
        className="flex space-x-6 mb-8"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <button
          onClick={() => setActiveTab("chat")}
          className={`flex items-center px-6 py-3 rounded-2xl shadow-lg text-lg font-medium transition-all duration-300 ${
            activeTab === "chat"
              ? "bg-blue-600 text-white scale-105"
              : "bg-gray-700 hover:bg-gray-600 text-gray-200"
          }`}
        >
          <MessageSquare className="w-5 h-5 mr-2" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab("docs")}
          className={`flex items-center px-6 py-3 rounded-2xl shadow-lg text-lg font-medium transition-all duration-300 ${
            activeTab === "docs"
              ? "bg-green-600 text-white scale-105"
              : "bg-gray-700 hover:bg-gray-600 text-gray-200"
          }`}
        >
          <Folder className="w-5 h-5 mr-2" />
          Documents
        </button>
      </motion.div>

      {/* Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -15 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-3xl bg-gray-900 border border-gray-700 shadow-2xl rounded-2xl p-8"
      >
        {activeTab === "chat" ? <ChatBox /> : <DocumentManager />}
      </motion.div>

    </div>
  );
}

export default App;
