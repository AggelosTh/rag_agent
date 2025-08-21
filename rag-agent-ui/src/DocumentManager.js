import { useState } from "react";
import { addDocument, removeDocument, searchDocument } from "./api";
import { motion } from "framer-motion";
import { Plus, Trash2, Search, FileText, Upload, CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function DocumentManager() {
  const [doc, setDoc] = useState({ doc_id: "", title: "", content: "" });
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState({ add: false, remove: false, search: false });
  const [notification, setNotification] = useState({ show: false, message: "", type: "" });

  const showNotification = (message, type) => {
    setNotification({ show: true, message, type });
    setTimeout(() => setNotification({ show: false, message: "", type: "" }), 3000);
  };

  const handleAdd = async () => {
    if (!doc.doc_id.trim() || !doc.title.trim() || !doc.content.trim()) {
      showNotification("Please fill in all fields", "error");
      return;
    }

    setIsLoading(prev => ({ ...prev, add: true }));
    try {
      const res = await addDocument(doc);
      showNotification("Document added successfully!", "success");
      setDoc({ doc_id: "", title: "", content: "" });
    } catch (error) {
      showNotification("Failed to add document", "error");
    } finally {
      setIsLoading(prev => ({ ...prev, add: false }));
    }
  };

  const handleRemove = async () => {
    if (!doc.doc_id.trim()) {
      showNotification("Please enter a Document ID", "error");
      return;
    }

    setIsLoading(prev => ({ ...prev, remove: true }));
    try {
      const res = await removeDocument(doc.doc_id);
      showNotification("Document removed!", "success");
      setDoc({ doc_id: "", title: "", content: "" });
    } catch (error) {
      showNotification("Failed to remove document", "error");
    } finally {
      setIsLoading(prev => ({ ...prev, remove: false }));
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      showNotification("Please enter a search query", "error");
      return;
    }

    setIsLoading(prev => ({ ...prev, search: true }));
    try {
      const res = await searchDocument(query);
      setResults(res);
      if (res.length === 0) {
        showNotification("No documents found", "error");
      } else {
        showNotification(`Found ${res.length} documents`, "success");
      }
    } catch (error) {
      showNotification("Search failed", "error");
      setResults([]);
    } finally {
      setIsLoading(prev => ({ ...prev, search: false }));
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="text-center mb-8 pb-6 border-b-2 border-gray-200">
        <div className="w-16 h-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-3xl font-black text-gray-800 mb-2">
          Document Manager
        </h2>
        <p className="text-gray-600 text-lg font-semibold">
          Add, remove, and search your documents
        </p>
      </div>

      {/* Notification */}
      {notification.show && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-6 p-4 rounded-xl font-bold flex items-center gap-3 ${
            notification.type === "success" 
              ? "bg-green-100 border-2 border-green-300 text-green-800"
              : "bg-red-100 border-2 border-red-300 text-red-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : (
            <XCircle className="w-5 h-5" />
          )}
          {notification.message}
        </motion.div>
      )}

      <div className="grid lg:grid-cols-2 gap-8 mb-8">
        
        {/* Add Document Section */}
        <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-2xl p-6 border-2 border-blue-200">
          <h3 className="text-xl font-black text-gray-800 mb-6 flex items-center gap-2">
            <Plus className="w-6 h-6 text-blue-600" />
            Add New Document
          </h3>

          <div className="space-y-4">
            <input
              className="w-full bg-white border-2 border-gray-300 rounded-xl px-4 py-3 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium"
              placeholder="Document ID (e.g., doc-001)"
              value={doc.doc_id}
              onChange={(e) => setDoc({ ...doc, doc_id: e.target.value })}
            />

            <input
              className="w-full bg-white border-2 border-gray-300 rounded-xl px-4 py-3 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium"
              placeholder="Document Title"
              value={doc.title}
              onChange={(e) => setDoc({ ...doc, title: e.target.value })}
            />

            <textarea
              className="w-full h-32 bg-white border-2 border-gray-300 rounded-xl px-4 py-3 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium resize-none"
              placeholder="Document content goes here..."
              value={doc.content}
              onChange={(e) => setDoc({ ...doc, content: e.target.value })}
            />

            <div className="flex gap-3">
              <button
                onClick={handleAdd}
                disabled={isLoading.add}
                className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isLoading.add ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Plus className="w-5 h-5" />
                )}
                Add Document
              </button>

              <button
                onClick={handleRemove}
                disabled={isLoading.remove}
                className="bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isLoading.remove ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Trash2 className="w-5 h-5" />
                )}
                Remove
              </button>
            </div>
          </div>
        </div>

        {/* Search Section */}
        <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-2xl p-6 border-2 border-yellow-200">
          <h3 className="text-xl font-black text-gray-800 mb-6 flex items-center gap-2">
            <Search className="w-6 h-6 text-orange-600" />
            Search Documents
          </h3>

          <div className="space-y-4">
            <input
              className="w-full bg-white border-2 border-gray-300 rounded-xl px-4 py-3 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 font-medium"
              placeholder="What are you looking for?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />

            <button
              onClick={handleSearch}
              disabled={isLoading.search}
              className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading.search ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
              Search Now
            </button>
          </div>
        </div>
      </div>

      {/* Search Results */}
      {results.length > 0 && (
        <div className="bg-gradient-to-br from-green-50 to-blue-50 rounded-2xl p-6 border-2 border-green-200">
          <h3 className="text-xl font-black text-gray-800 mb-6 flex items-center gap-2">
            <FileText className="w-6 h-6 text-green-600" />
            Search Results ({results.length})
          </h3>

          <div className="space-y-4 max-h-80 overflow-y-auto">
            {results.map((result, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-xl p-5 border-2 border-gray-200 shadow-lg"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                        <FileText className="w-4 h-4 text-white" />
                      </div>
                      <span className="font-bold text-gray-800">
                        Result #{index + 1}
                      </span>
                    </div>
                    <div className="text-gray-700 font-medium leading-relaxed">
                      {result.content || result}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {results.length === 0 && !isLoading.search && (
        <div className="text-center py-12 bg-gray-50 rounded-2xl border-2 border-gray-200">
          <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-xl font-bold text-gray-600">No search results yet</p>
          <p className="text-gray-500 font-medium mt-2">Use the search box above to find documents</p>
        </div>
      )}
    </div>
  );
}