import ChatBox from "./ChatBox";
import DocumentManager from "./DocumentManager";

function App() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">RAG Agent UI</h1>
      <ChatBox />
      <DocumentManager />
    </div>
  );
}

export default App;
