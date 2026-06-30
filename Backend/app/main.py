from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid
import traceback
from .services.ai_handler import AIHandler
from .services.file_parser import FileParser
from .utils.utils import logger
from .services.conversation_store import ConversationStore
from .core.config import LOGS_DIR

class AnalysisResponseModel(BaseModel):
    analysis: str
    conversation_id: str

class ChatHistoryItem(BaseModel):
    sender: str
    content: str
    timestamp: str
    
    # Allow additional fields for file attachments
    class Config:
        extra = "allow"

class ChatMessage(BaseModel):
    personality_id: str
    message: str
    file_content: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    
    @validator('personality_id')
    def validate_personality_id(cls, v):
        if v not in ["1", "2", "3", "4", "5", "6"]:
            raise ValueError(f"Invalid personality ID: {v}. Must be between 1 and 6.")
        return v
    

app = FastAPI(title="Choosable Chatbot API")

# Initialize AI handler
ai_handler = AIHandler()

# Initialize conversation store
conversation_store = ConversationStore()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers to ensure preflight requests work properly
    expose_headers=["Content-Disposition"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Ensure backend logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)


@app.options("/upload-log")
async def upload_log_options():
    """
    Handle OPTIONS request for upload-log endpoint
    """
    return {"message": "OK"}


@app.get("/")
async def root():
    return {"message": "Welcome to the Choosable Chatbot API"}


@app.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message: str = Form(...),
    files: List[UploadFile] = File([])
):
    """
    Add a message to a conversation and get AI response
    """
    try:
        # Get conversation
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        personality_id = conversation["personality_id"]
        logger.info(f"Adding message to conversation {conversation_id} for personality {personality_id}")
        
        # Process files if provided
        file_attachments = []
        parsed_contents = []
        
        for i, file in enumerate(files):
            if file and file.filename:
                logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}, type: {file.content_type}")
                
                # Read file content
                file_content = await file.read()
                
                # Create file attachment info
                file_info = {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(file_content)
                }
                
                try:
                    # Parse file content
                    parsed_content, content_type = FileParser.parse_file(
                        file_content, file.filename, file.content_type or ''
                    )
                    
                    # Ensure parsed_content is a string for JSON serialization
                    if isinstance(parsed_content, bytes):
                        try:
                            # Try to decode as UTF-8
                            string_content = parsed_content.decode('utf-8')
                        except UnicodeDecodeError:
                            # If that fails, use base64 encoding
                            import base64
                            string_content = f"[Binary content encoded as base64: {base64.b64encode(parsed_content).decode('ascii')}]"
                    else:
                        string_content = str(parsed_content)
                    
                    # Store parsed content directly in the message
                    file_info["parsed_content"] = string_content
                    file_info["content_type"] = content_type
                    
                    # Add to parsed contents for AI context
                    parsed_contents.append({
                        "filename": file.filename,
                        "content": string_content,
                        "type": content_type
                    })
                    
                    logger.info(f"Parsed content for file {file.filename}, type: {content_type}, size: {len(string_content)} characters")
                    
                    # For debugging purposes
                    with open(f"uploaded_{file.filename}", "wb") as f:
                        f.write(file_content)
                    logger.info(f"Saved uploaded file for debugging: uploaded_{file.filename}")
                    
                except Exception as parse_error:
                    logger.error(f"Error parsing file {file.filename}: {str(parse_error)}")
                    file_info["parse_error"] = str(parse_error)
                
                # Add to file attachments
                file_attachments.append(file_info)
        
        # Add user message to conversation
        user_message = conversation_store.add_message(
            conversation_id,
            "user",
            message,
            file_attachments
        )
        
        # Prepare AI context with file contents
        ai_context = message
        if parsed_contents:
            for i, file_data in enumerate(parsed_contents):
                ai_context += f"\n\nAttached file {i+1}: {file_data['filename']} (Type: {file_data['type']})\n"
                ai_context += file_data['content']
        
        # Get AI response
        ai_response = ai_handler.get_response(
            personality_id,
            ai_context
        )
        
        # Add AI response to conversation
        bot_message = conversation_store.add_message(
            conversation_id,
            "bot",
            ai_response
        )
        
        return {
            "user_message": user_message,
            "bot_message": bot_message
        }
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding message: {str(e)}")



@app.get("/conversations/{conversation_id}/analyze", response_model=AnalysisResponseModel)
async def analyze_conversation_endpoint(conversation_id: str):
    """
    Analyze a conversation and return the analysis.
    """
    try:
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Analysis requested for non-existent conversation: {conversation_id}")
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        if not conversation.get("messages"):
            logger.warning(f"Analysis requested for conversation {conversation_id} with no messages")
            return AnalysisResponseModel(analysis="No messages in this conversation to analyze.", conversation_id=conversation_id)

        # TODO: tu moram namesto pošiljanja zgolj messagov, predati celotni conversation objekt 
        # # -> popraviti moraš pričakovani input parameter v analyze_conversation_text ter samo funkcijo
        #messages_for_analysis = conversation.get("messages", [])
        #logger.info(f"Calling AIHandler to analyze conversation {conversation_id} with {len(messages_for_analysis)} messages.")
        #personality_id_for_context = conversation.get("personality_id")
        analysis_text = ai_handler.analyze_conversation_text(conversation)

        logger.info(f"Successfully generated analysis for conversation {conversation_id}")
        return AnalysisResponseModel(analysis=analysis_text, conversation_id=conversation_id)
    except HTTPException: # Re-raise HTTPException to ensure FastAPI handles it
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation {conversation_id}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error analyzing conversation: {str(e)}")
    
# New conversation-based API endpoints
@app.post("/conversations")
async def create_conversation(personality_id: str = Form(...)):
    """
    Create a new conversation with a specific personality
    """
    try:
        # Validate personality_id
        if personality_id not in ["1", "2", "3", "4", "5", "6"]:
            raise HTTPException(status_code=400, detail=f"Invalid personality ID: {personality_id}. Must be between 1 and 6.")
        
        conversation_id = conversation_store.create_conversation(personality_id)
        return {"conversation_id": conversation_id, "personality_id": personality_id}
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")


@app.post("/conversations/{conversation_id}/export")
async def export_conversation_endpoint(conversation_id: str):
    """
    Export a conversation as a JSON file.
    """
    try:
        # Get the conversation
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Export requested for non-existent conversation: {conversation_id}")
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        # Create a unique filename
        personality_id = conversation.get("personality_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_with_personality_{personality_id}_{timestamp}.json"
        
        # Use backend logs directory for exported conversation files
        log_dir = LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Write conversation to file
        file_path = log_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported conversation {conversation_id} to {file_path}")
        
        # Set proper headers for JSON file download
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/json",
            headers=headers
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation {conversation_id}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error exporting conversation: {str(e)}")
    
@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get a conversation by ID
    """
    try:
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")
    
@app.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """
    Get all messages in a conversation
    """
    try:
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return {"messages": conversation["messages"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")
    

@app.post("/upload-log")
async def upload_log(file: UploadFile = File(...)):
    """
    Process an uploaded JSON log file
    """
    logger.info(f"Received upload request for file: {file.filename}")
    
    # Check if the file has a valid extension
    if not file.filename.endswith('.json'):
        logger.warning(f"Invalid file extension: {file.filename}")
        return {"status": "error", "message": "Only JSON (.json) files are supported"}
    
    try:
        # Read and parse the uploaded file
        logger.info(f"Received upload of {file.filename}")
        content = await file.read()
        try:
            conversation = json.loads(content)
            logger.info(f"Successfully parsed JSON from {file.filename}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")

        #****************** VALIDATE CONVERSATION FILE STRUCTURE ******************

        # Extract conversation ID if present in the original data
        try:
            conversation_id = conversation.get("id")
            if conversation_id is None:
                raise HTTPException(status_code=400, detail="Missing 'id' in root JSON object")
        except Exception as e:
            logger.error(f"Error extracting conversation ID: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting conversation ID: {str(e)}")

        # Extract personality ID from the data
        try:
            personality_id = conversation.get("personality_id")
            if personality_id is None:
                raise HTTPException(status_code=400, detail="Missing 'personality_id' in root JSON object")
        except Exception as e:
            logger.error(f"Error extracting personality ID: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting personality ID: {str(e)}")

        # Validate message structure
        try:
            chat_history_messages = conversation.get("messages")
            if not isinstance(chat_history_messages, list):
                logger.error("Chat history is not a list")
                raise HTTPException(status_code=400, detail="Chat history is not a list")
            # validate messages contins sender, content and optionaly file_attachment
            for message in chat_history_messages:
                if not isinstance(message, dict):
                    logger.error("Message is not a dictionary")
                    raise HTTPException(status_code=400, detail="Message is not a dictionary")

                if not isinstance(message["sender"], str):
                    logger.error("Message sender is not a string")
                    raise HTTPException(status_code=400, detail="Message sender is not a string")

                if not isinstance(message["content"], str):
                    logger.error("Message content is not a string")
                    raise HTTPException(status_code=400, detail="Message content is not a string")

                if "file_attachments" in message:
                    if not isinstance(message["file_attachments"], list):
                        logger.error("File attachments is not a list")
                        raise HTTPException(status_code=400, detail="File attachments is not a list")

                    for file_attachment in message["file_attachments"]:
                        if not isinstance(file_attachment, dict):
                            logger.error("File attachment is not a dictionary")
                            raise HTTPException(status_code=400, detail="File attachment is not a dictionary")

                        if not isinstance(file_attachment["filename"], str):
                            logger.error("File attachment filename is not a string")
                            raise HTTPException(status_code=400, detail="File attachment filename is not a string")

                        if not isinstance(file_attachment["content_type"], str):
                            logger.error("File attachment content_type is not a string")
                            raise HTTPException(status_code=400, detail="File attachment content_type is not a string")

                        if not isinstance(file_attachment["size"], int):
                            logger.error("File attachment size is not an integer")
                            raise HTTPException(status_code=400, detail="File attachment size is not an integer")

                        if not isinstance(file_attachment["parsed_content"], str):
                            logger.error("File attachment parsed_content is not a string")
                            raise HTTPException(status_code=400, detail="File attachment parsed_content is not a string")

        except Exception as e:
            logger.error(f"Error extracting chat history messages: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting chat history messages: {str(e)}")

        #****************** SAVE, LOAD AND INITIALIZE AI FULL CONVERSATION HISTORY WITH ATTACHED FILES - used for storing full conversation to local disk and loading it back ******************
        personality_id, conversation = conversation_store._setup_conversation_history(conversation_id, conversation)
        ai_handler.initialize_chat_history(personality_id, conversation)
        #****************** PREPARE FRONTEND CONVERSATION DISPLAY WITHOUT ATTACHED FILES ******************
        # Process each entry in the chat history
        chat_history = []
        for entry in conversation.get("messages"):
            # Preserve original message ID if present
            message_id = entry.get("id", str(uuid.uuid4()))
            
            sender = entry["sender"].lower() if isinstance(entry["sender"], str) else ""
            content = entry["content"] if isinstance(entry["content"], str) else ""
            
            # Preserve original timestamp if present
            timestamp = entry.get("timestamp")
            if not timestamp:
                timestamp = datetime.now().isoformat()

            # Map sender to 'user' or 'bot'
            if sender in ["user", "human", "me"]:
                sender = "user"
            elif sender in ["bot", "ai", "assistant", "chatbot"]:
                sender = "bot"
            else:
                # Skip entries with invalid sender
                continue
            
            # Extract file attachments if present
            # Identify file attachments in the message
            file_keys = [k for k in entry.keys() if k.startswith('file_attachments')]
            logger.info(f"Found file attachments in message: {file_keys}")
            
            file_attachments = []
            for key in file_keys:
                if entry[key]:  # Ensure the value is not empty
                    attachment = entry[key]
                    # If it's already a list of attachments, use them directly
                    if isinstance(attachment, list) and all(isinstance(item, dict) for item in attachment):
                        file_attachments.extend(attachment)
                # If it's a single attachment dict, add it
                elif isinstance(attachment, dict):
                    file_attachments.append(attachment)
                else:
                    # Otherwise create a simple attachment dict
                    file_attachments.append({
                        "filename": attachment,
                        "content_type": "text/plain",
                        "parsed_content": str(attachment)
                    })
            
            message_entry = {
                "id": message_id,
                "sender": sender,
                "content": content,
                "timestamp": timestamp
            }
            
            # Only add file_attachments if there are any
            if file_attachments:
                message_entry["file_attachments"] = file_attachments
                
            chat_history.append(message_entry)
            
        logger.info(f"Successfully parsed {len(chat_history)} messages from {file.filename}")
        

        return {
            "conversation_id": conversation_id,
            "personality_id": personality_id,
            "chat_history": chat_history
        }
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing uploaded file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
