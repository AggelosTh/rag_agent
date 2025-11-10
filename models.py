from typing import Optional, TypedDict

from pydantic import BaseModel, Field


class AgentState(TypedDict):
    user_input: str
    retrieved_docs: Optional[list]
    response: Optional[str]
    doc_id: Optional[str]
    new_title: Optional[str]
    new_content: Optional[str]
    intent: Optional[str]
    summaries: Optional[list]
    summarized_docs: Optional[str]
    search_result: Optional[dict]
    extracted_info: Optional[dict]
    
class Document(BaseModel):
    doc_id: str = Field(description="Unique identifier for the document")
    title: Optional[str] = Field(default="", description="Document title")
    content: Optional[str] = Field(default="", description="Document content")

class DocumentRequest(BaseModel):
    doc_id: str
    title: Optional[str]
    content: Optional[str]

class UpdateDocumentRequest(BaseModel):
    doc_id: str
    new_title: str
    new_content: Optional[str] = None