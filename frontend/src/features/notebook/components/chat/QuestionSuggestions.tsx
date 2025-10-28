import React from 'react';
import { Button } from '@/shared/components/ui/button';

interface QuestionSuggestionsProps {
  onSuggestionClick: (suggestion: string) => void;
}

const suggestions = [
  "Can you summarize the key findings?",
  "What are the main arguments in the document?",
];

const QuestionSuggestions: React.FC<QuestionSuggestionsProps> = ({ onSuggestionClick }) => {
  return (
    <div className="p-4 bg-white">
      <h4 className="text-sm font-semibold text-gray-600 mb-2">Suggested Questions</h4>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            onClick={() => onSuggestionClick(suggestion)}
            className="text-xs"
          >
            {suggestion}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default QuestionSuggestions;