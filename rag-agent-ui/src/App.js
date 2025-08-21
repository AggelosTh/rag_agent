import { useState } from "react";
import ChatBox from "./ChatBox";
import DocumentManager from "./DocumentManager";
import { motion } from "framer-motion";
import { MessageSquare, Folder } from "lucide-react";

function App() {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-500 text-white flex flex-col items-center justify-center p-8">
      
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-12"
      >
        <h1 className="text-6xl font-black mb-4 text-white drop-shadow-lg">
          RAG Assistant
        </h1>
      </motion.div>

      {/* Tabs */}
      <div className="flex space-x-4 mb-8">
        <button
          onClick={() => setActiveTab("chat")}
          className={`flex items-center px-8 py-4 rounded-xl text-lg font-bold transition-all duration-300 ${
            activeTab === "chat"
              ? "bg-white text-purple-600 shadow-xl"
              : "bg-purple-800/50 hover:bg-purple-700/50 text-white"
          }`}
        >
          <MessageSquare className="w-6 h-6 mr-3" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab("docs")}
          className={`flex items-center px-8 py-4 rounded-xl text-lg font-bold transition-all duration-300 ${
            activeTab === "docs"
              ? "bg-white text-purple-600 shadow-xl"
              : "bg-purple-800/50 hover:bg-purple-700/50 text-white"
          }`}
        >
          <Folder className="w-6 h-6 mr-3" />
          Documents
        </button>
      </div>

      {/* Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-6xl"
      >
        {activeTab === "chat" ? <ChatBox /> : <DocumentManager />}
      </motion.div>

    </div>
  );
}

export default App;