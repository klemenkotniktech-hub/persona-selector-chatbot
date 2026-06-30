
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { personalities } from '../data/personalities.ts';
import { usePersonality } from '../context/PersonalityContext.tsx';

const PersonalitySelectionPage: React.FC = () => {
  const navigate = useNavigate();
  const { setSelectedPersonality } = usePersonality();

  const handlePersonalitySelect = (personalityId: string) => {
    const personality = personalities.find(p => p.id === personalityId);
    if (personality) {
      setSelectedPersonality(personality);
      navigate('/chat');
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6 text-center">Select a Personality</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        {personalities.map((personality) => (
          <div 
            key={personality.id} 
            className="flex flex-col items-center p-4 border rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => handlePersonalitySelect(personality.id)}
          >
            <div className="w-32 h-32 rounded-full mb-4 overflow-hidden border-2 border-blue-500">
              <img 
                src={personality.imagePath} 
                alt={personality.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Fallback if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.onerror = null;
                  target.src = '';
                  target.parentElement!.classList.add('bg-gray-200', 'flex', 'items-center', 'justify-center');
                  const span = document.createElement('span');
                  span.className = 'text-gray-500 text-2xl';
                  span.textContent = personality.name[0];
                  target.parentElement!.appendChild(span);
                  target.style.display = 'none';
                }}
              />
            </div>
            <h2 className="text-lg font-medium">{personality.name}</h2>
            <p className="text-sm text-gray-600 text-center mt-2">{personality.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PersonalitySelectionPage;