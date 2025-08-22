import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000", // FastAPI base URL
});

// Agent query
export const processQuery = async (user_input) => {
  const res = await API.post("/process", null, { params: { user_input } });
  return res.data.response;
};

// Add document
export const addDocument = async (doc) => {
  const res = await API.post("/add_document", doc);
  return res.data.response;
};

export const removeDocument = async (doc_id) => {
  const res = await API.post(
    "/remove_document",
    { doc_id: doc_id },   // explicit mapping
    { headers: { "Content-Type": "application/json" } }
  );
  return res.data.response;
};


// Search document
export const searchDocument = async (query) => {
  const res = await API.post("/search_document", null, { params: { query } });
  return res.data.retrieved_docs || [];
};
