import os
import sys
import traceback
import json
import base64
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage, AIMessage
from langchain.schema.document import Document
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from ..utils.utils import logger
from .file_parser import FileParser
from .content_moderation import ContentModerator

# Load environment variables from .env file
load_dotenv()

# Centralized safety guidelines to be applied to all personalities
SAFETY_GUIDELINES = """

IMPORTANT SAFETY GUIDELINES:
- Never provide advice or information that could be used for illegal activities
- Do not engage with content related to violence, harm, or illegal activities
- If asked about harmful, violent, or inappropriate topics, politely redirect the conversation
- Do not provide instructions on how to create weapons, harmful substances, or engage in harmful activities
- Maintain ethical standards in all responses and avoid content that promotes discrimination
- Do not provide medical advice that could lead to harm or substitute for professional medical care
- Avoid generating content that could be used for harassment, exploitation, or harm to individuals or groups
- If unsure about the safety of a topic, err on the side of caution and provide general information only
"""

# Dictionary of personality descriptions for the AI
PERSONALITY_DESCRIPTIONS = {
    "1": """You are an accountant chatbot. Be professional, precise, and focused on financial matters.
    Speak with authority on accounting principles, tax regulations, financial planning, and budgeting.
    Use formal language and occasionally reference accounting standards or tax codes.
    Be helpful but maintain a professional demeanor at all times.""",
    
    "2": """You are a childhood friend chatbot. Be casual, warm, and nostalgic.
    Use informal language, reference shared childhood experiences, and be supportive.
    Your tone should be friendly and personal, as if you've known the person for many years.
    Feel free to use casual expressions, light humor, and show genuine care for your friend.""",
    
    "3": """You are a clinical psychologist chatbot. Be empathetic, thoughtful, and supportive.
    Focus on understanding emotions, providing therapeutic insights, and asking meaningful questions.
    Maintain a professional but warm demeanor, and avoid making definitive diagnoses.
    Use reflective listening techniques and suggest coping strategies when appropriate.""",
    
    "4": """You are a doctor chatbot. Be professional, informative, and focused on health matters.
    Provide general medical information while being clear about your limitations.
    Use medical terminology appropriately but explain concepts in accessible ways.
    Always remind users to consult with real healthcare professionals for specific medical advice.""",
    
    "5": """You are an engineer chatbot. Be analytical, precise, and solution-oriented.
    Discuss technical concepts, engineering principles, and problem-solving approaches.
    Use technical terminology when appropriate and focus on practical applications.
    Be methodical in your explanations and consider efficiency and optimization.""",
    
    "6": """You are a lawyer chatbot. Be formal, precise, and knowledgeable about legal concepts.
    Discuss legal principles and considerations while being clear about jurisdictional limitations.
    Use legal terminology appropriately and structure your responses carefully.
    Always remind users that you're providing general information, not legal advice."""
}

class AIHandler:
    def __init__(self, api_key: Optional[str] = None, skip_connection_test: bool = False):
        """
        Initialize the AI Handler
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
            skip_connection_test: If True, skips the initial connection test (useful for quota issues)
        """
        # Flag to track if API is available
        self.api_available = False
        self.api_error_message = None
        
        try:
            # Use provided API key or get from environment
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            
            if not self.api_key:
                logger.error("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
                self.api_error_message = "No OpenAI API key found. Please set the OPENAI_API_KEY environment variable."
                return
                
            logger.info(f"API key loaded successfully: {self.api_key[:5]}...{self.api_key[-4:]}")
            print(f"API key loaded successfully: {self.api_key[:5]}...{self.api_key[-4:]}")
            
            # Initialize the ChatOpenAI model
            self.chat_model = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                openai_api_key=self.api_key,
                verbose=True
            )
            
            # Initialize chat history storage for each personality
            self.chat_histories = {}
            
            # Initialize content moderator
            try:
                self.content_moderator = ContentModerator(api_key=self.api_key)
                logger.info("Content moderator initialized successfully")
            except Exception as moderator_error:
                logger.error(f"Error initializing content moderator: {str(moderator_error)}")
                print(f"Error initializing content moderator: {str(moderator_error)}")
                # Continue without moderation if it fails
                self.content_moderator = None
            
            # Skip connection test if requested (useful when dealing with quota issues)
            if skip_connection_test:
                logger.info("Skipping OpenAI connection test")
                print("Skipping OpenAI connection test")
                self.api_available = True
                return
                
            # Test the connection with a simple message
            try:
                test_messages = [
                    SystemMessage(content="You are a helpful assistant."),
                    HumanMessage(content="Hello")
                ]
                test_response = self.chat_model.invoke(test_messages)
                logger.info(f"Test connection successful: {test_response.content}")
                print(f"LangChain connection test successful: {test_response.content}")
                self.api_available = True
            except Exception as e:
                logger.error(f"Test connection failed: {str(e)}")
                print(f"Test connection failed: {str(e)}")
                self.api_error_message = str(e)
                # Don't raise the exception, just log it and continue in fallback mode
            
            logger.info("AI Handler initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing AI Handler: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"Error initializing AI Handler: {str(e)}")
    
    def initialize_chat_history(self, personality_id: str, chat_history: list) -> None:
        """
        Initialize the chat history for a specific personality
        
        Args:
            personality_id: ID of the personality (1-6)
            chat_history: List of chat history items with sender and content
        """
        try:
            if personality_id not in self.chat_histories:
                self.chat_histories[personality_id] = []
            
            # Convert chat history to LangChain message format
            messages = []
            for item in chat_history:
                sender = item.get('sender', '').lower()
                content = item.get('content', '')
                
                # Check for file attachments and append their content to the message
                file_attachments = item.get('file_attachments', [])
                if file_attachments and isinstance(file_attachments, list):
                    logger.info(f"Found {len(file_attachments)} file attachments in message")
                    for attachment in file_attachments:
                        # Handle different attachment formats
                        if isinstance(attachment, dict):
                            # Get the filename
                            filename = attachment.get('filename', '')
                            
                            # Try different fields for content based on the format
                            parsed_content = attachment.get('parsed_content', '')
                            content_type = attachment.get('content_type', '')
                            
                            # If we have content_type but no parsed_content, the content might be in other fields
                            if not parsed_content and content_type:
                                # Try common field names for content
                                for field in ['content', 'text', 'data', 'size', 'value']:
                                    if field in attachment and attachment[field]:
                                        parsed_content = attachment[field]
                                        logger.info(f"Found content in '{field}' field for {filename}")
                                        break
                            
                            # Log what we found
                            logger.info(f"Processing attachment: filename={filename}, content_type={content_type}, has_content={bool(parsed_content)}")
                            
                            # Add the content to the message if we have both filename and content
                            if filename and parsed_content:
                                content += f"\n\nAppended file: {filename}\n\nContent:\n{parsed_content}\n\n"
                                logger.info(f"Added file attachment: {filename} to message content")
                            elif filename:
                                # If we have a filename but no content, at least mention the file
                                content += f"\n\nAppended file: {filename} (content not available)\n\n"
                                logger.info(f"Added file reference without content: {filename}")
                        else:
                            # Unknown format, log it
                            logger.warning(f"Unknown file attachment format: {type(attachment)}, value: {attachment}")
                            
                # After processing all attachments, log the final content (first 100 chars only)
                try:
                    # Use ASCII-only representation to avoid encoding issues
                    safe_content = content[:100].encode('ascii', 'replace').decode('ascii')
                    logger.info(f"Final message content with attachments: {safe_content}...")
                except Exception as log_error:
                    logger.error(f"Error logging message content: {str(log_error)}")


                
                if sender == 'user':
                    messages.append(HumanMessage(content=content))
                elif sender == 'bot':
                    messages.append(AIMessage(content=content))
            
            # Store the messages - limit logging to avoid encoding issues with non-ASCII characters
            try:
                # Only log the number of messages, not their full content to avoid encoding issues
                logger.info(f"Processed {len(messages)} messages for chat history")
            except Exception as log_error:
                logger.error(f"Error logging messages: {str(log_error)}")
        
            self.chat_histories[personality_id] = messages
            
            logger.info(f"Initialized chat history for personality {personality_id} with {len(messages)} messages")
            
            # Process the chat history with the LLM to help it understand the context
            self.process_chat_history(personality_id)
        except Exception as e:
            logger.error(f"Error initializing chat history: {str(e)}")
            logger.error(traceback.format_exc())
            
    def process_chat_history(self, personality_id: str) -> None:
        """
        Process the chat history with the LLM to help it understand the context without expecting a response.
        This helps the model build a better understanding of the conversation flow for more natural continuation.
        
        Args:
            personality_id: ID of the personality (1-6)
        """
        try:
            # Check if we have chat history for this personality
            if personality_id not in self.chat_histories or not self.chat_histories[personality_id]:
                logger.info(f"No chat history to process for personality {personality_id}")
                return
                
            # Get the personality description and append safety guidelines
            personality_desc = PERSONALITY_DESCRIPTIONS.get(personality_id)
            
            if not personality_desc:
                logger.warning(f"Invalid personality ID: {personality_id}")
                return
                
            # Append safety guidelines to the personality description
            personality_desc = personality_desc + SAFETY_GUIDELINES
            
            # Create the messages for LangChain, including chat history
            messages = [SystemMessage(content=personality_desc)]
            messages.extend(self.chat_histories[personality_id])
            
            # Add a special message instructing the model to just understand the context
            context_message = """The above is the conversation history. Please read and understand it to maintain context for future interactions. 
            No response is needed at this time. This is just to help you understand the conversation flow."""
            messages.append(HumanMessage(content=context_message))
            
            # Send to the LLM but ignore the response
            logger.info(f"Processing chat history for personality {personality_id} with {len(self.chat_histories[personality_id])} messages")
            _ = self.chat_model.invoke(messages)
            logger.info(f"Successfully processed chat history for personality {personality_id}")
        except Exception as e:
            logger.error(f"Error processing chat history: {str(e)}")
            logger.error(traceback.format_exc())
            # Continue even if there's an error with processing chat history
    
    def get_response(self, personality_id: str, message: str, file_content: str = None, file_name: str = None, file_type: str = None) -> str:
        """
        Get a response from the AI based on the personality and message
        
        Args:
            personality_id: ID of the personality (1-6)
            message: User's message
            file_content: Optional base64-encoded file content
            file_name: Optional name of the attached file
            file_type: Optional MIME type of the attached file
            
        Returns:
            AI response
        """
        # Check if API is available, if not return a fallback message
        if not hasattr(self, 'api_available') or not self.api_available:
            error_details = self.api_error_message if hasattr(self, 'api_error_message') and self.api_error_message else "Unknown error"
            return f"I'm sorry, but I'm currently unable to process your request due to an API connection issue: {error_details}. Please try again later or contact support for assistance."
            
        try:
            # Get the personality description and append safety guidelines
            personality_desc = PERSONALITY_DESCRIPTIONS.get(personality_id)
            
            if not personality_desc:
                logger.warning(f"Invalid personality ID: {personality_id}")
                return "I'm sorry, there was an issue with my configuration. Please try again."
            
            # Append safety guidelines to the personality description
            personality_desc = personality_desc + SAFETY_GUIDELINES
            
            logger.info(f"Processing message for personality {personality_id}: {message[:50]}...")
            
            # Prepare the user message with file content if provided
            user_message = message
            
            # Check user input for harmful content if content moderator is available
            if hasattr(self, 'content_moderator') and self.content_moderator:
                logger.info("Checking user input with content moderator")
                filtered_message, is_harmful = self.content_moderator.filter_harmful_content(message, is_user_input=True)
                
                if is_harmful:
                    logger.warning(f"User input for personality {personality_id} was flagged as harmful")
                    return filtered_message
            
            # Process file attachment if provided
            if file_content and file_name:
                logger.info(f"File attachment included: {file_name}, type: {file_type or 'unknown'}, size: {len(file_content)} characters")
                
                # Check if the content is already parsed (string) or needs parsing
                if isinstance(file_content, str):
                    # Content is already parsed
                    parsed_content = file_content
                    content_type = file_type or 'text'
                    logger.info(f"Using pre-parsed file content for {file_name}")
                else:
                    # Content needs parsing
                    try:
                        # Parse the file content based on file type
                        parsed_content, content_type = FileParser.parse_file(file_content, file_name, file_type or '')
                        logger.info(f"Successfully parsed file {file_name} as {content_type}")
                    except Exception as parse_error:
                        logger.error(f"Error parsing file {file_name}: {str(parse_error)}")
                        user_message = f"{message}\n\nAttached file: {file_name} (Error: Could not parse file content)"
                        # Skip the rest of the file processing by setting a flag
                        parsed_content = None
                        content_type = None
                
                # Only process the content if parsing was successful
                if parsed_content is not None and content_type is not None:
                    # Truncate parsed content if it's too large to avoid token limits
                    max_content_length = 100000  # Adjust based on your token limits
                    if len(parsed_content) > max_content_length:
                        parsed_content = parsed_content[:max_content_length] + "\n\n[Content truncated due to size...]"
                    
                    # Add file information to the user message
                    file_info = f"\n\nAttached file: {file_name} (Type: {content_type})\n"
                    user_message = f"{message}{file_info}\n{parsed_content}"
            
            # Create the messages for LangChain, including chat history if available
            messages = [SystemMessage(content=personality_desc)]
            
            # Add chat history if available for this personality
            if hasattr(self, 'chat_histories') and personality_id in self.chat_histories and self.chat_histories[personality_id]:
                logger.info(f"Adding {len(self.chat_histories[personality_id])} previous messages from chat history")
                messages.extend(self.chat_histories[personality_id])
            
            # Add the current message
            messages.append(HumanMessage(content=user_message))

            # Get the response from LangChain
            try:
                response = self.chat_model.invoke(messages)
                
                # Extract the response content
                if hasattr(response, 'content'):
                    response_content = response.content
                else:
                    # Fallback for different response formats
                    response_content = str(response)
                
                logger.info(f"Received response from LangChain: {response_content[:50]}...")
                
                # Check AI output for harmful content if content moderator is available
                if hasattr(self, 'content_moderator') and self.content_moderator:
                    logger.info("Checking AI output with content moderator")
                    filtered_response, is_harmful = self.content_moderator.filter_harmful_content(response_content, is_user_input=False)
                    
                    if is_harmful:
                        logger.warning(f"AI output for personality {personality_id} was flagged as harmful")
                        response_content = filtered_response
                
                # Update chat history with this interaction
                if not hasattr(self, 'chat_histories'):
                    self.chat_histories = {}
                    
                if personality_id not in self.chat_histories:
                    self.chat_histories[personality_id] = []
                
                # Add the user message and AI response to the history
                self.chat_histories[personality_id].append(HumanMessage(content=user_message))
                self.chat_histories[personality_id].append(AIMessage(content=response_content))
                
                return response_content
                
            except Exception as e:
                logger.error(f"Error in LangChain call: {str(e)}")
                print(f"Error in LangChain call: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error during conversation analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return "I'm sorry, I encountered an issue performing the conversation analysis. Please try again later."


    def analyze_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """
        Analyze a given conversation using the AI model.

        Args:
            conversation: A conversation dictionary.

        Returns:
            A string containing the AI's analysis of the conversation.
        """
        personality_id = conversation.get("personality_id")
        conversation_string = json.dumps(conversation)
        logger.info(f"Starting analysis for a conversation with {len(conversation_string)} messages. Personality ID: {personality_id}")
        if not conversation_string:
            logger.warning("Attempted to analyze an empty conversation.")
            return "The conversation is empty and cannot be analyzed."

        try:
            logger.info(f"Conversation string: {conversation_string[:500]}")
            # Define the system prompt for analysis
            analysis_prompt_template = f"""
            You are an AI assistant tasked with analyzing a conversation. Please review the following conversation text carefully:
            --- CONVERSATION START ---
            {conversation_string}
            --- CONVERSATION END ---

            Based on this conversation, please provide a concise and objective analysis covering the following aspects:
            1.  **Summary**: A brief overview of what the conversation was about (2-3 sentences).
            2.  **Key Topics**: List the 3-5 main subjects or themes discussed.
            3.  **Overall Sentiment**: Describe the general emotional tone of the conversation (e.g., positive, negative, neutral, mixed, inquisitive, frustrated, etc.). Provide a brief justification.
            4.  **Key Insights/Observations**: Note any significant patterns, user goals or intentions if apparent, unresolved questions, or particularly interesting interactions (2-3 points).

            Present your analysis clearly. Ensure your output is structured with these headings.
            {SAFETY_GUIDELINES}
            """

            langchain_messages = [SystemMessage(content=analysis_prompt_template)]

            # Get the analysis from LangChain
            response = self.chat_model.invoke(langchain_messages)
            analysis_content = getattr(response, 'content', str(response))

            logger.info(f"Received analysis from LangChain: {analysis_content[:150]}...")

            # Check AI output for harmful content
            if hasattr(self, 'content_moderator') and self.content_moderator:
                logger.info("Checking AI-generated analysis with content moderator")
                filtered_analysis, is_harmful = self.content_moderator.filter_harmful_content(analysis_content, is_user_input=False)
                if is_harmful:
                    logger.warning("AI-generated analysis was flagged as harmful and modified.")
                    analysis_content = filtered_analysis
            
            return analysis_content

        except Exception as e:
            logger.error(f"Error during conversation analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return "I'm sorry, I encountered an issue performing the conversation analysis. Please try again later."