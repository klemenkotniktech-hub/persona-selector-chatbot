import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/Button.tsx';
import Header from '../components/Header.tsx';
import Card from '../components/Card.tsx';
import Footer from '../components/Footer.tsx';
import { ChatIcon, UploadIcon, InfoIcon } from '../components/Icons.tsx';
import { uploadChatLog } from '../services/api.ts';
import { usePersonality } from '../context/PersonalityContext.tsx';
import { Personality } from '../data/personalities.ts';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [showInfo, setShowInfo] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setSelectedPersonality, setImportedChatHistory } = usePersonality();

  const handleNewChat = () => {
    navigate('/select-personality');
  };

  const handleContinueChat = () => {
    // Open file picker to upload .xlsx log
    fileInputRef.current?.click();
  };
  
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Only accept JSON files
    if (!file.name.endsWith('.json')) {
      setError('Only JSON (.json) files are supported');
      return;
    };

    setError(null);
    setIsLoading(true);

    try {
      console.log(`Attempting to upload file: ${file.name}`);
      const response = await uploadChatLog(file);
      console.log('Upload response:', response);
      
      // Log detailed structure of the response for debugging
      console.log('Response structure details:');
      console.log('- personality_id:', response.personality_id);
      console.log('- conversation_id:', response.conversation_id);
      console.log('- chat_history type:', response.chat_history ? Array.isArray(response.chat_history) ? 'array' : typeof response.chat_history : 'undefined');
      console.log('- chat_history length:', response.chat_history?.length || 0);
      
      // Simplified validation for latest functionality only
      if (response.chat_history && response.personality_id && response.conversation_id) {
        // Ensure chat_history is an array
        const chatHistory = response.chat_history;
        
        // Validate chat history has at least one message
        if (!chatHistory.length) {
          setError('The uploaded file does not contain any valid chat messages.');
          return;
        }

        console.log(`Found ${chatHistory.length} messages with personality ID: ${response.personality_id}`);
        
        // Set the personality based on the chat history
        const personalityName = getPersonalityName(response.personality_id);
        console.log(`Using personality: ${personalityName}`);
        
        setSelectedPersonality({
          id: response.personality_id,
          name: personalityName,
          description: `${personalityName} personality from imported chat history`,
          imagePath: `/assets/personalities/${personalityName}.jpg`
        } as Personality);
        
        // Store the imported chat history in context
        const formattedHistory = chatHistory.map((msg: any, index) => ({
          id: msg.id || `imported-${index}`,
          sender: msg.sender as 'user' | 'bot',
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          // Preserve file attachments if they exist
          file_attachments: msg.file_attachments || undefined
        }));
        
        console.log(`Processed ${formattedHistory.length} chat messages for import`);
        console.log('Sample formatted message:', formattedHistory.length > 0 ? formattedHistory[0] : 'No messages');
        setImportedChatHistory(formattedHistory);
        
        // Store the conversation ID in sessionStorage
        console.log(`Storing conversation ID in sessionStorage: ${response.conversation_id}`);
        sessionStorage.setItem('importedConversationId', response.conversation_id);
        
        // Navigate to chat page
        navigate('/chat');
      } else {
        console.error('Invalid response format:', response);
        setError('Invalid chat history file. The file must contain chat history, personality ID, and conversation ID.');
      }

      // Reset the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      console.error('Error uploading file:', err);
      // Extract more detailed error message if available
      const errorMessage = err.message || 'Failed to upload file. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Helper function to get personality name from ID
  const getPersonalityName = (id: string): string => {
    const personalities: {[key: string]: string} = {
      "1": "Accountant",
      "2": "Childhood Friend",
      "3": "Clinical Psychologist",
      "4": "Doctor",
      "5": "Engineer",
      "6": "Lawyer"
    };
    return personalities[id] || "Unknown";
  };

  const toggleInfo = () => {
    setShowInfo(!showInfo);
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <main className="flex-grow flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-4xl">
          <Header 
            title="Choosable Chatbot" 
            subtitle="Select a personality and start chatting"
          />
          
          {/* Hidden file input for uploading chat history */}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
            accept=".json"
          />
          
          {/* Error message display */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6">
              {error}
            </div>
          )}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-center mb-6">
              <div className="loader mr-2"></div>
              <span>Processing file...</span>
            </div>
          )}
          
          {showInfo ? (
            <div className="bg-white rounded-lg shadow-md p-6 mb-8 animate-fade-in">
              <h2 className="text-2xl font-semibold mb-4 text-blue-600">About Choosable Chatbot</h2>
              <p className="mb-4">Choosable Chatbot allows you to select from 6 different AI personalities and have conversations with them based on your preference.</p>
              <p className="mb-4">You can start a new chat or continue a previous conversation by uploading your chat history.</p>
              <div className="mt-6">
                <Button onClick={toggleInfo} variant="secondary">Back to Main Menu</Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <Card
                title="Start New Chat"
                description="Select a personality and begin a new conversation"
                icon={<ChatIcon className="h-8 w-8" />}
                onClick={handleNewChat}
                className="border-2 border-transparent hover:border-blue-500"
                disabled={isLoading}
              />
              <Card
                title="Continue Previous Chat"
                description="Upload a conversation log to continue where you left off"
                icon={<UploadIcon className="h-8 w-8" />}
                onClick={handleContinueChat}
                className="border-2 border-transparent hover:border-blue-500"
                disabled={isLoading}
              />
            </div>
          )}
          
          {!showInfo && (
            <div className="text-center">
              <Button 
                onClick={toggleInfo}
                variant="secondary"
                className="inline-flex items-center"
                disabled={isLoading}
              >
                <InfoIcon className="mr-2" /> About Choosable Chatbot
              </Button>
            </div>
          )}
        </div>
      </main>
      <Footer />
      
      {/* Loader style */}
      <style dangerouslySetInnerHTML={{ __html: `
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
      `}} />
    </div>
  );
};

export default LandingPage;