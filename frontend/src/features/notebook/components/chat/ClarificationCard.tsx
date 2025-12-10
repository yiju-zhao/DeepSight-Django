/**
 * Clarification Card Component
 *
 * A special UI card that displays clarification questions from the Coordinator.
 * Shows the question, its purpose, and optional quick-reply buttons.
 */

import React from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/utils/utils';

interface ClarificationQuestion {
    question: string;
    purpose: string;
    required: boolean;
}

interface ClarificationCardProps {
    questions: ClarificationQuestion[];
    message?: string;
    onRespond?: (response: string) => void;
    onSkip?: () => void;
    className?: string;
}

// Quick response suggestions based on common clarification types
const QUICK_RESPONSES = [
    'Please proceed with what you have',
    'Focus on the most important aspects',
    'I want a comprehensive overview',
];

const ClarificationCard: React.FC<ClarificationCardProps> = ({
    questions,
    message,
    onRespond,
    onSkip,
    className,
}) => {
    const [isExpanded, setIsExpanded] = React.useState(true);

    return (
        <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.2 }}
            className={cn(
                'bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl',
                'border border-amber-200/60 shadow-sm',
                'overflow-hidden',
                className
            )}
        >
            {/* Header */}
            <div className="px-5 py-4 border-b border-amber-200/40 bg-gradient-to-r from-amber-100/50 to-transparent">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center">
                        <HelpCircle className="h-4 w-4 text-white" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-amber-900">
                            Clarification Needed
                        </h3>
                        {message && (
                            <p className="text-xs text-amber-700 mt-0.5">{message}</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Questions */}
            <div className="px-5 py-4 space-y-3">
                {questions.map((q, index) => (
                    <div
                        key={index}
                        className="bg-white/60 rounded-lg px-4 py-3 border border-amber-100"
                    >
                        <div className="flex items-start gap-2">
                            <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium flex items-center justify-center flex-shrink-0 mt-0.5">
                                {index + 1}
                            </span>
                            <div className="flex-1">
                                <p className="text-sm text-gray-800 font-medium">{q.question}</p>
                                {q.purpose && (
                                    <p className="text-xs text-gray-500 mt-1">
                                        <span className="italic">Why: </span>
                                        {q.purpose}
                                    </p>
                                )}
                                {q.required && (
                                    <span className="inline-block mt-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">
                                        Required
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Quick Responses */}
            {onRespond && (
                <div className="px-5 pb-4">
                    <p className="text-xs text-gray-500 mb-2">Quick responses:</p>
                    <div className="flex flex-wrap gap-2">
                        {QUICK_RESPONSES.map((response, index) => (
                            <Button
                                key={index}
                                variant="outline"
                                size="sm"
                                onClick={() => onRespond(response)}
                                className="h-7 px-3 text-xs bg-white hover:bg-amber-50 border-amber-200 text-amber-700"
                            >
                                {response}
                            </Button>
                        ))}
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="px-5 py-3 bg-amber-50/50 border-t border-amber-200/40 flex items-center justify-between">
                <p className="text-xs text-amber-600">
                    Type your response in the chat below
                </p>
                {onSkip && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onSkip}
                        className="text-xs text-amber-600 hover:text-amber-800 hover:bg-amber-100"
                    >
                        Skip & Proceed
                        <ArrowRight className="h-3 w-3 ml-1" />
                    </Button>
                )}
            </div>
        </motion.div>
    );
};

export default React.memo(ClarificationCard);
