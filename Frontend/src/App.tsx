import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { PersonalityProvider } from './context/PersonalityContext.tsx';
import LandingPage from './pages/LandingPage.tsx';
import PersonalitySelectionPage from './pages/PersonalitySelectionPage.tsx';
import ChatPage from './pages/ChatPage.tsx';

function App() {
  return (
    <PersonalityProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/select-personality" element={<PersonalitySelectionPage />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </div>
      </Router>
    </PersonalityProvider>
  );
}

export default App;