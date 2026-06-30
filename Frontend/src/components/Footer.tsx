import React from 'react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="mt-auto py-4 text-center text-gray-500 text-sm">
      <p>© {currentYear} Choosable Chatbot. All rights reserved.</p>
    </footer>
  );
};

export default Footer;