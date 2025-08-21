import { useState } from "react";
import { addDocument, removeDocument, searchDocument } from "./api";

export default function DocumentManager() {
  const [doc, setDoc] = useState({ doc_id: "", title: "", content: "" });
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const handleAdd = async () => {
    const res = await addDocument(doc);
    alert(res);
  };

  const handleRemove = async () => {
    const res = await removeDocument(doc.doc_id);
    alert(res);
  };

  const handleSearch = async () => {
    const res = await searchDocument(query);
    setResults(res);
  };

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h2 className="text-xl font-bold mb-2">Document Manager</h2>
      <input
        className="border p-2 w-full mb-2"
        placeholder="Doc ID"
        value={doc.doc_id}
        onChange={(e) => setDoc({ ...doc, doc_id: e.target.value })}
      />
      <input
        className="border p-2 w-full mb-2"
        placeholder="Title"
        value={doc.title}
        onChange={(e) => setDoc({ ...doc, title: e.target.value })}
      />
      <textarea
        className="border p-2 w-full mb-2"
        placeholder="Content"
        value={doc.content}
        onChange={(e) => setDoc({ ...doc, content: e.target.value })}
      />
      <button className="bg-green-500 text-white px-4 py-2 rounded mr-2" onClick={handleAdd}>
        Add Document
      </button>
      <button className="bg-red-500 text-white px-4 py-2 rounded" onClick={handleRemove}>
        Remove Document
      </button>

      <hr className="my-4" />
      <input
        className="border p-2 w-full mb-2"
        placeholder="Search query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={handleSearch}>
        Search
      </button>
      <ul className="mt-4">
        {results.map((r, i) => (
          <li key={i} className="border p-2 mb-2">{r.content}</li>
        ))}
      </ul>
    </div>
  );
}
