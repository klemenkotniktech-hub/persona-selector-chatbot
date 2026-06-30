import React, { ReactNode } from 'react';

export interface CardProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

const Card: React.FC<CardProps> = ({ 
  title, 
  description, 
  icon, 
  onClick, 
  className = '',
  disabled = false
}) => {
  return (
    <div 
      className={`bg-white rounded-lg shadow-md p-6 transition-all ${disabled ? 'opacity-60 cursor-not-allowed' : 'hover:shadow-lg cursor-pointer'} ${className}`}
      onClick={disabled ? undefined : onClick}
    >
      <div className="flex items-center mb-4">
        {icon && <div className="mr-4 text-blue-500">{icon}</div>}
        <h3 className="text-xl font-semibold">{title}</h3>
      </div>
      {description && <p className="text-gray-600">{description}</p>}
    </div>
  );
};

export default Card;