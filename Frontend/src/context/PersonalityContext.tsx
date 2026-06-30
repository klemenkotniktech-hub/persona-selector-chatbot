import React, { createContext, useState, useContext, ReactNode } from 'react';
import { Personality } from '../data/personalities';

// Define the ChatMessage interface
export interface FileAttachment {
  filename: string;
  content_type: string;
  size?: number;
  parsed_content?: string;
  parsed_file_path?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  content: string;
  timestamp: string;
  file_attachments?: FileAttachment[];
}

interface PersonalityContextType {
  selectedPersonality: Personality | null;
  setSelectedPersonality: (personality: Personality) => void;
  importedChatHistory: ChatMessage[];
  setImportedChatHistory: (history: ChatMessage[]) => void;
  clearImportedChatHistory: () => void;
}

const PersonalityContext = createContext<PersonalityContextType | undefined>(undefined);

export const PersonalityProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPersonality, setSelectedPersonality] = useState<Personality | null>(null);
  const [importedChatHistory, setImportedChatHistory] = useState<ChatMessage[]>([]);

  const clearImportedChatHistory = () => {
    setImportedChatHistory([]);
  };

  return (
    <PersonalityContext.Provider value={{
      selectedPersonality,
      setSelectedPersonality,
      importedChatHistory,
      setImportedChatHistory,
      clearImportedChatHistory
    }}>
      {children}
    </PersonalityContext.Provider>
  );
};

export const usePersonality = (): PersonalityContextType => {
  const context = useContext(PersonalityContext);
  if (context === undefined) {
    throw new Error('usePersonality must be used within a PersonalityProvider');
  }
  return context;
};