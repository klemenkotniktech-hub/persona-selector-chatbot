// API service for making requests to the backend

const API_BASE_URL = 'http://localhost:8000';

// Interfaces for the new conversation-based API
export interface Conversation {
  id: string;
  personality_id: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface ConversationMessage {
  id: string;
  sender: 'user' | 'bot';
  content: string;
  timestamp: string;
  file_attachments?: FileAttachment[];
}

export interface FileAttachment {
  filename: string;
  content_type: string;
  size: number;
  parsed_file_path?: string;
}

export interface ChatRequest {
  message: string;
  personalityId: string;  // Changed to camelCase for frontend consistency
  file?: File;           // Now using the File object directly
}

export interface ChatResponse {
  response: string;
  timestamp: string;
}

export interface FileUploadResponse {
  message: string;
  status: string;
  personality_id?: string;
  conversation_id?: string; // New field for the conversation ID
  chat_history?: Array<{
    sender: 'user' | 'bot';
    content: string;
    timestamp: string;
    file_attachments?: FileAttachment[];
  }>;
}

/**
 * Create a new conversation
 */
export const createConversation = async (personalityId: string): Promise<{ conversation_id: string; personality_id: string }> => {
  try {
    const formData = new FormData();
    formData.append('personality_id', personalityId);
    
    const response = await fetch(`${API_BASE_URL}/conversations`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error creating conversation:', error);
    throw error;
  }
};

/**
 * Get a conversation by ID
 */
export const getConversation = async (conversationId: string): Promise<Conversation> => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting conversation:', error);
    throw error;
  }
};

/**
 * Get messages in a conversation
 */
export const getMessages = async (conversationId: string): Promise<{ messages: ConversationMessage[] }> => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting messages:', error);
    throw error;
  }
};

/**
 * Add a message to a conversation
 */
export const addMessage = async (
  conversationId: string,
  message: string,
  files?: File[]
): Promise<{ user_message: ConversationMessage; bot_message: ConversationMessage }> => {
  try {
    const formData = new FormData();
    formData.append('message', message);
    
    // Add files if they exist
    if (files && files.length > 0) {
      files.forEach(file => {
        formData.append('files', file);
        console.log(`Adding file to form data: ${file.name}`);
      });
    }
    
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding message:', error);
    throw error;
  }
};

/**
 * Export a conversation
 */
export const exportConversation = async (conversationId: string): Promise<Blob> => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/export`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return await response.blob();
  } catch (error) {
    console.error('Error exporting conversation:', error);
    throw error;
  }
};

/**
 * Upload a chat log file to the backend API
 */
export const uploadChatLog = async (file: File): Promise<FileUploadResponse> => {
  try {
    console.log(`Uploading file: ${file.name}, size: ${file.size} bytes, type: ${file.type}`);
    
    // Validate file is JSON
    if (!file.name.endsWith('.json')) {
      throw new Error('Only JSON (.json) files are supported');
    }
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);

    // Add a timestamp to prevent caching issues
    const url = `${API_BASE_URL}/upload-log?t=${new Date().getTime()}`;
    console.log(`Sending request to: ${url}`);

    try {
      // Log the request details
      console.log('Sending request with the following details:');
      console.log('- URL:', url);
      console.log('- Method: POST');
      console.log('- File name:', file.name);
      console.log('- File size:', file.size);
      console.log('- File type:', file.type);
      
      // Make the request
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        // Add headers to prevent caching
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        },
        // Add timeout and credentials options
        credentials: 'same-origin'
      });

      console.log(`Response status: ${response.status} ${response.statusText}`);
      // Log headers in a way that's compatible with TypeScript
      const headerObj: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headerObj[key] = value;
      });
      console.log('Response headers:', headerObj);

      // Handle non-OK responses with more detailed error information
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error response body: ${errorText}`);
        let errorDetail = '';
        
        try {
          // Try to parse the error as JSON
          const errorJson = JSON.parse(errorText);
          errorDetail = errorJson.detail || errorJson.message || errorText;
          console.log('Parsed error JSON:', errorJson);
        } catch (parseError) {
          // If not JSON, use the raw text
          console.error('Error parsing error response:', parseError);
          errorDetail = errorText;
        }
        
        console.error(`API error (${response.status}): ${errorDetail}`);
        
        // Provide more specific error messages based on status code
        if (response.status === 400) {
          throw new Error(`Invalid file format: ${errorDetail}`);
        } else if (response.status === 413) {
          throw new Error('File too large. Please upload a smaller file.');
        } else if (response.status === 415) {
          throw new Error('Unsupported file type. Please upload a JSON file.');
        } else {
          throw new Error(`Error uploading file: ${errorDetail}`);
        }
      }

      // Try to parse the response as JSON
      try {
        const responseText = await response.text();
        console.log(`Response body (first 200 chars): ${responseText.substring(0, 200)}...`);
        
        // Parse the JSON manually after logging it
        const result = JSON.parse(responseText);
        console.log('Upload successful, parsed result:', result);
        return result;
      } catch (jsonError) {
        console.error('Error parsing JSON response:', jsonError);
        throw new Error('Invalid response format from server');
      }
    } catch (networkError: any) {
      console.error('Network error during fetch:', networkError);
      
      // Provide more detailed error messages based on the error type
      if (networkError.name === 'TypeError' && networkError.message.includes('Failed to fetch')) {
        throw new Error('Network error: Unable to connect to the server. Please check if the backend server is running.');
      } else if (networkError.name === 'AbortError') {
        throw new Error('Network error: Request timed out. Please try again.');
      } else {
        throw new Error(`Network error: ${networkError?.message || 'Failed to connect to server'}`);
      }
    }
  } catch (error) {
    console.error('Error uploading chat log:', error);
    throw error;
  }
};

// Interface for the chat analysis response
export interface AnalysisResponse {
  analysis: string;
  conversation_id: string;
}

/**
 * Analyze a conversation
 */
export const analyzeChat = async (conversationId: string): Promise<AnalysisResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/analyze`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorDetail = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorJson.message || errorText;
      } catch (parseError) {
        // If not JSON, use the raw text
      }
      console.error(`API error (${response.status}) analyzing chat: ${errorDetail}`);
      throw new Error(`Failed to analyze chat: ${errorDetail}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error analyzing chat:', error);
    throw error;
  }
};