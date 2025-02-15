from typing import TypedDict, Optional
from pydantic import BaseModel

class AgentState(TypedDict):
    user_input: str
    retrieved_docs: Optional[list]
    response: Optional[str]
    doc_id: Optional[str]
    new_title: Optional[str]
    new_content: Optional[str]

class DocumentRequest(BaseModel):
    doc_id: str
    title: Optional[str]
    content: Optional[str]

class UpdateDocumentRequest(BaseModel):
    doc_id: str
    new_title: str
    new_content: Optional[str] = None