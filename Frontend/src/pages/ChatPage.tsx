import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePersonality, ChatMessage } from '../context/PersonalityContext.tsx';
import Button from '../components/Button.tsx';
import { 
  createConversation,
  addMessage,
  exportConversation,
  analyzeChat
} from '../services/api.ts';

// Utility function to format file size in a human-readable format
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' bytes';
  else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  else return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedPersonality, importedChatHistory, clearImportedChatHistory } = usePersonality();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

  // Redirect to personality selection if no personality is selected
  useEffect(() => {
    if (!selectedPersonality) {
      navigate('/select-personality');
    } else if (!conversationId) {
      // Create a new conversation when a personality is selected
      const initConversation = async () => {
        try {
          const result = await createConversation(selectedPersonality.id);
          setConversationId(result.conversation_id);
          console.log(`Created new conversation: ${result.conversation_id}`);
        } catch (err) {
          console.error('Error creating conversation:', err);
          setError('Failed to initialize chat. Please try again.');
        }
      };
      
      initConversation();
    }
  }, [selectedPersonality, navigate, conversationId]);
  
  // Load imported chat history if available
  useEffect(() => {
    if (importedChatHistory.length > 0) {
      // Check if we have a conversation ID in sessionStorage from an imported chat
      const importedConversationId = sessionStorage.getItem('importedConversationId');
      if (importedConversationId) {
        setConversationId(importedConversationId);
        // Clear the stored ID to prevent reuse
        sessionStorage.removeItem('importedConversationId');
        console.log(`Using imported conversation ID: ${importedConversationId}`);
      }
      
      setMessages(importedChatHistory);
      // Clear the imported history to prevent reloading on component remounts
      clearImportedChatHistory();
    }
  }, [importedChatHistory, clearImportedChatHistory]);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedPersonality || !conversationId || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Convert single file attachment to array format required by API
    const filesToSend = attachedFile ? [attachedFile] : [];
    
    // Prepare message content (include file attachment info if present)
    let messageContent = inputValue;
    if (attachedFile) {
      messageContent += `\n\nAttached file: ${attachedFile.name} (${formatFileSize(attachedFile.size)})`;
      console.log(`Preparing to send message with attached file: ${attachedFile.name}`);
      console.log(`File type: ${attachedFile.type}, size: ${attachedFile.size} bytes`);
    }

    // Create temporary message object to show immediately in UI
    const tempUserMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      content: messageContent,
      timestamp: new Date().toISOString(),
    };

    // Update UI immediately
    setMessages([...messages, tempUserMessage]);
    setInputValue('');
    
    try {
      // Send message to API using the new conversation-based approach
      const response = await addMessage(
        conversationId,
        inputValue, // Send only the original input, not the combined message
        filesToSend
      );

      // Replace temporary message with actual message from server
      const userMessage = response.user_message;
      const botMessage = response.bot_message;
      
      // Convert to ChatMessage format for UI
      const userChatMessage: ChatMessage = {
        id: userMessage.id,
        sender: userMessage.sender,
        content: userMessage.content,
        timestamp: userMessage.timestamp,
        file_attachments: userMessage.file_attachments,
      };
      
      const botChatMessage: ChatMessage = {
        id: botMessage.id,
        sender: botMessage.sender,
        content: botMessage.content,
        timestamp: botMessage.timestamp,
        file_attachments: botMessage.file_attachments,
      };
      
      // Update messages, replacing the temporary message
      setMessages(prev => [
        ...prev.slice(0, prev.length - 1), // Remove temporary message
        userChatMessage,
        botChatMessage
      ]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);

    // Maximum file size (5MB)
    const MAX_FILE_SIZE = 5 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
      setError(`File is too large. Maximum size is 5MB.`);
      return;
    }

    // Check if file type is supported
    const fileExtension = file.name.split('.').pop()?.toLowerCase() || '';
    const supportedExtensions = [
      // Text files
      'txt', 'md', 'js', 'ts', 'py', 'html', 'css', 'java', 'c', 'cpp',
      // PDFs
      'pdf',
      // Word documents
      'docx', 'doc',
      // RTF
      'rtf',
      // CSV/Excel
      'csv', 'xlsx', 'xls',
      // JSON/XML
      'json', 'xml',
      // Images
      'jpg', 'jpeg', 'png', 'gif', 'bmp'
    ];

    if (!supportedExtensions.includes(fileExtension)) {
      setError(`File type .${fileExtension} is not supported. Please upload one of the following: text files, PDFs, CSV, JSON/XML, or images.`);
      return;
    }

    // With the new API, we don't need to read file content in the frontend
    // Just store the file object for sending later
    setAttachedFile(file);
    setError(`File "${file.name}" attached. Type your message and send.`);
    
    // Reset the file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleEndChatClick = () => {
    setShowEndConfirm(true);
  };

  const handleExportChat = async () => {
    if (!selectedPersonality || !conversationId || messages.length === 0 || isExporting) return;
    
    setIsExporting(true);
    setError(null);
    
    try {
      // Use the new conversation-based export API
      const blob = await exportConversation(conversationId);
      
      console.log(`Exporting conversation ${conversationId} with ${messages.length} messages`);
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const fileDownloadLink = document.createElement('a');
      fileDownloadLink.href = url;
      fileDownloadLink.download = `chat_with_${selectedPersonality.name}_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(fileDownloadLink);
      fileDownloadLink.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(fileDownloadLink);
    } catch (err) {
      console.error('Error exporting chat:', err);
      setError('Failed to export chat history. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleAnalyzeChat = async () => {
    if (!conversationId || messages.length === 0) {
      setError("Cannot analyze an empty or uninitialized chat.");
      return;
    }
    setError(null);
    setIsAnalyzing(true);
    try {
      const result = await analyzeChat(conversationId);
      setAnalysisResult(result.analysis);
      setShowAnalysisModal(true);
      setShowEndConfirm(false); // Close the end chat confirmation modal
    } catch (err) {
      console.error('Error analyzing chat:', err);
      setError('Failed to analyze chat. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleEndChatConfirm = () => {
    navigate('/');
  };

  const handleEndChatCancel = () => {
    setShowEndConfirm(false);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header with personality info */}
      <header className="bg-blue-500 text-white p-4 flex items-center">
        <div className="w-10 h-10 rounded-full mr-3 overflow-hidden border-2 border-white">
          {selectedPersonality?.imagePath ? (
            <img 
              src={selectedPersonality.imagePath} 
              alt={selectedPersonality.name}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback if image fails to load
                const target = e.target as HTMLImageElement;
                target.onerror = null;
                target.src = '';
                target.parentElement!.classList.add('bg-gray-200', 'flex', 'items-center', 'justify-center');
                const span = document.createElement('span');
                span.className = 'text-gray-500';
                span.textContent = selectedPersonality.name[0];
                target.parentElement!.appendChild(span);
                target.style.display = 'none';
              }}
            />
          ) : (
            <div className="w-full h-full bg-gray-200 flex items-center justify-center">
              <span className="text-gray-500">{selectedPersonality?.name[0]}</span>
            </div>
          )}
        </div>
        <h1 className="text-xl font-semibold">{selectedPersonality?.name}</h1>
      </header>

      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 italic">Start a conversation with {selectedPersonality?.name}</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs md:max-w-md p-3 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-blue-500 text-white rounded-br-none'
                    : 'bg-gray-200 text-gray-800 rounded-bl-none'
                }`}
              >
                <p>{message.content}</p>
                {message.file_attachments && message.file_attachments.length > 0 && (
                  <div className="mt-2 border-t pt-2 border-opacity-20 border-gray-400">
                    <p className="text-xs font-semibold mb-1">File Attachments:</p>
                    {message.file_attachments.map((attachment, idx) => (
                      <div key={idx} className="flex items-center text-xs">
                        <span className="mr-1">📎</span>
                        <span className="truncate">{attachment.filename}</span>
                        {attachment.size && <span className="ml-1">({formatFileSize(attachment.size)})</span>}
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs mt-1 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
            {error}
          </div>
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 p-3 rounded-lg rounded-bl-none flex items-center">
              <div className="loader mr-2"></div>
              <span>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        {/* Attached file indicator */}
        {attachedFile && (
          <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg flex justify-between items-center">
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span className="text-sm text-blue-700">{attachedFile.name} attached</span>
            </div>
            <button 
              onClick={() => {
                setAttachedFile(null);
                setFileContent(null);
                setError(null);
              }}
              className="text-blue-500 hover:text-blue-700"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        
        <div className="flex items-center">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
          />
          <button
            onClick={handleFileUploadClick}
            className="p-2 text-gray-500 hover:text-gray-700 flex items-center justify-center"
            title="Attach a file"
            disabled={isLoading || attachedFile !== null}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder={attachedFile ? "Type your message with the attached file..." : "Type your message..."}
            className="flex-1 p-2 border rounded-lg mx-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <Button 
            onClick={handleSendMessage} 
            disabled={isLoading || !inputValue.trim()}
          >
            Send
          </Button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          AI-generated responses may be inaccurate or misleading. Always verify information from reliable sources.
        </p>
      </div>

      {/* END button */}
      <div className="p-4 border-t">
        <Button
          onClick={handleEndChatClick}
          variant="secondary"
          className="w-full"
          disabled={isLoading}
        >
          END
        </Button>
      </div>

      {/* End Chat Confirmation Modal */}
      {showEndConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h3 className="text-xl font-semibold mb-4">End Chat</h3>
            <p className="mb-6">Are you sure you want to end this chat? You can export the chat history before ending.</p>
            <div className="flex justify-between items-center">
              <div className="flex space-x-2"> {/* Group for Export and Analyze buttons */}
                <Button 
                  variant="secondary" 
                  onClick={handleExportChat}
                  disabled={isExporting || messages.length === 0 || isAnalyzing}
                >
                  {isExporting ? 'Exporting...' : 'Export Chat'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleAnalyzeChat}
                  disabled={isAnalyzing || messages.length === 0 || isExporting}
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Chat'}
                </Button>
              </div>
              <div className="space-x-4">
                <Button variant="secondary" onClick={handleEndChatCancel} disabled={isAnalyzing || isExporting}>Cancel</Button>
                <Button onClick={handleEndChatConfirm} disabled={isAnalyzing || isExporting}>End Chat</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Display Modal */}
      {showAnalysisModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-lg w-full">
            <h3 className="text-xl font-semibold mb-4">Chat Analysis</h3>
            <div className="mb-6 max-h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm">{analysisResult}</pre>
            </div>
            <div className="flex justify-end">
              <Button 
                variant="secondary" 
                onClick={() => {
                  setShowAnalysisModal(false);
                  setAnalysisResult(null); // Clear result when closing
                }}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Add some CSS for the loading indicator
const styles = `
  .loader {
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

export default ChatPage;