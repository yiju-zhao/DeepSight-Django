import React from 'react';
import { Button } from '@/shared/components/ui/button';

interface QuestionSuggestionsProps {
  suggestions: string[];
  onSuggestionClick: (suggestion: string) => void;
}

const QuestionSuggestions: React.FC<QuestionSuggestionsProps> = ({ suggestions, onSuggestionClick }) => {
  return (
    <div className="p-4 bg-white">
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            onClick={() => onSuggestionClick(suggestion)}
            className="text-xs rounded-lg p-4"
          >
            {suggestion}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default QuestionSuggestions;