from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatMessage(BaseModel):
    message: str
    personality_id: str
    file_content: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: str

class HistoryEntry(BaseModel):
    timestamp: str
    speaker: str  # "User" or "Bot"
    message_type: str  # "Text" or "File + Text"
    content: str
    attached_file: Optional[str] = None

class ChatHistory(BaseModel):
    personality: str
    entries: List[HistoryEntry]