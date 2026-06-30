import os
from typing import Tuple, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from ..utils.utils import logger

# Load environment variables
load_dotenv()

class ContentModerator:
    """
    Content moderation using OpenAI's Moderation API
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the content moderator
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("No OpenAI API key found")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info("Content moderator initialized")
    
    def check_content(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check content using OpenAI's moderation API
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_flagged, categories)
        """
        try:
            if not text or not text.strip():
                return False, {}
                
            response = self.client.moderations.create(input=text)
            result = response.results[0]
            
            # Extract flagged categories for logging
            flagged_categories = {
                k: v for k, v in result.categories.model_dump().items() if v
            }
            
            # Get category scores for more detailed analysis
            category_scores = result.category_scores.model_dump()
            
            # Log moderation results if flagged
            if result.flagged:
                logger.warning(f"Content moderation flagged content: {flagged_categories}")
                logger.info(f"Content scores: {category_scores}")
                
                # Log a sample of the flagged content (first 100 chars)
                content_sample = text[:100] + "..." if len(text) > 100 else text
                logger.warning(f"Flagged content sample: {content_sample}")
            
            return result.flagged, {
                "flagged": result.flagged,
                "categories": flagged_categories,
                "category_scores": category_scores
            }
            
        except Exception as e:
            logger.error(f"Error in content moderation: {str(e)}")
            # Default to safe if moderation API fails to avoid blocking legitimate content
            return False, {}
    
    def filter_harmful_content(self, content: str, is_user_input: bool = False) -> Tuple[str, bool]:
        """
        Filter content for harmful material and return a safe version
        
        Args:
            content: The content to filter
            is_user_input: Whether this is user input (True) or AI output (False)
            
        Returns:
            Tuple of (filtered_content, is_harmful)
        """
        is_flagged, moderation_result = self.check_content(content)
        
        if is_flagged:
            # Different responses based on whether it's user input or AI output
            if is_user_input:
                # For user input, we return a polite refusal message
                logger.warning("User input was flagged as harmful")
                return (
                    "I'm sorry, but I cannot respond to that type of content. "
                    "Please ask me something else that aligns with my purpose as a helpful assistant.",
                    True
                )
            else:
                # For AI output, we provide a more generic response
                logger.warning("AI output was flagged as harmful")
                return (
                    "I apologize, but I cannot provide information on that topic. "
                    "Is there something else I can help you with?",
                    True
                )
        
        # Content is safe, return as is
        return content, False