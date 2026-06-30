import json
from datetime import datetime
from pathlib import Path
import uuid
import os
import logging
from typing import Dict, List, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

class ConversationStore:
    def __init__(self, storage_dir="./conversations"):
        """
        Initialize the conversation store
        
        Args:
            storage_dir: Directory to store conversation files
        """
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_conversations = {}  # In-memory cache
        
        logger.info(f"Initialized ConversationStore with storage at {self.storage_dir}")
    
    def create_conversation(self, personality_id: str) -> str:
        """
        Create a new conversation and return its ID
        
        Args:
            personality_id: ID of the personality (1-6)
            
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conversation = {
            "id": conversation_id,
            "personality_id": personality_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": []
        }
        
        # Save to disk
        self._save_conversation(conversation)
        
        # Cache in memory
        self.active_conversations[conversation_id] = conversation
        
        logger.info(f"Created new conversation {conversation_id} for personality {personality_id}")
        return conversation_id
    
    def add_message(self, conversation_id: str, sender: str, content: str, 
                    file_attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Add a message to an existing conversation
        
        Args:
            conversation_id: ID of the conversation
            sender: 'user' or 'bot'
            content: Message content
            file_attachments: List of file attachment information
            
        Returns:
            The added message
        """
        if conversation_id not in self.active_conversations:
            # Load from disk if not in memory
            self._load_conversation(conversation_id)
        
        conversation = self.active_conversations[conversation_id]
        
        message = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add file attachments if provided
        if file_attachments and len(file_attachments) > 0:
            message["file_attachments"] = file_attachments
            logger.info(f"Added {len(file_attachments)} file attachments to message in conversation {conversation_id}")
        
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()
        
        # Save to disk
        self._save_conversation(conversation)
        
        logger.info(f"Added {sender} message to conversation {conversation_id}")
        return message
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation data or None if not found
        """
        if conversation_id not in self.active_conversations:
            try:
                # Load from disk if not in memory
                self._load_conversation(conversation_id)
            except ValueError:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
        
        return self.active_conversations.get(conversation_id)
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of messages
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        return conversation["messages"]
    
    # We no longer need methods to store and retrieve file content as we'll store it directly in the message
    
    def export_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Export a conversation with all messages and file content
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation data
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Create a deep copy to avoid modifying the original
        export_data = json.loads(json.dumps(conversation))
        
        return export_data
    
    def _save_conversation(self, conversation: Dict[str, Any]) -> None:
        """
        Save conversation to disk
        
        Args:
            conversation: Conversation data
        """
        file_path = self.storage_dir / f"{conversation['id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
    
    def _load_conversation(self, conversation_id: str) -> None:
        """
        Load conversation from disk
        
        Args:
            conversation_id: ID of the conversation
            
        Raises:
            ValueError: If conversation not found
        """
        file_path = self.storage_dir / f"{conversation_id}.json"
        if not file_path.exists():
            raise ValueError(f"Conversation {conversation_id} not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
        
        self.active_conversations[conversation_id] = conversation
        logger.info(f"Loaded conversation {conversation_id} from disk")

    def _setup_conversation_history(self, conversation_id: str, conversation: Dict[str, Any]) -> None:
        """
        Save and load conversation to disk and initialize AI chat history
        
        Args:
            conversation_id: ID of the conversation
            conversation: Conversation data
            
        Raises:
            ValueError: If conversation not found
        """
        try:
            # Save to disk using the ConversationStore's method
            self._save_conversation(conversation)
            logger.info(f"Imported conversation was saved to conversations/{conversation_id}.json")

            # Load from disk
            self._load_conversation(conversation_id)
            logger.info(f"Imported conversation was loaded.")
        except Exception as e:
            logger.error(f"Error saving or loading imported conversation: {str(e)}")

        # Initialize the AI chat history with the parsed messages
        try:
            personality_id = conversation.get("personality_id")
            logger.info(f"Initializing AI chat history for personality {personality_id}")
            return personality_id, conversation 
        except Exception as e:
            logger.error(f"Error initializing AI chat history: {str(e)}")
            # Continue even if AI initialization fails