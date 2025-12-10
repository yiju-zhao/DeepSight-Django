/**
 * Task Progress Card Component
 *
 * Displays the progress of a coordinator task execution,
 * showing research and writing steps with status indicators.
 */

import React from 'react';
import { Search, FileText, Loader2, Check, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/shared/utils/utils';

interface ProgressStep {
    step: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    message?: string;
}

interface TaskProgressCardProps {
    taskId: string;
    steps: ProgressStep[];
    currentStep?: string;
    className?: string;
}

const stepConfig: Record<string, { icon: React.ElementType; label: string }> = {
    research: { icon: Search, label: 'Research' },
    writing: { icon: FileText, label: 'Writing' },
    default: { icon: Loader2, label: 'Processing' },
};

const statusStyles: Record<string, { bg: string; text: string; icon: string }> = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-500', icon: 'text-gray-400' },
    running: { bg: 'bg-blue-50', text: 'text-blue-600', icon: 'text-blue-500' },
    completed: { bg: 'bg-green-50', text: 'text-green-600', icon: 'text-green-500' },
    failed: { bg: 'bg-red-50', text: 'text-red-600', icon: 'text-red-500' },
};

const TaskProgressCard: React.FC<TaskProgressCardProps> = ({
    taskId,
    steps,
    currentStep,
    className,
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                'bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden',
                className
            )}
        >
            {/* Header */}
            <div className="px-5 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
                <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                    <span className="text-sm font-medium text-gray-700">Task in Progress</span>
                </div>
            </div>

            {/* Steps */}
            <div className="p-4 space-y-3">
                {steps.map((step, index) => {
                    const config = stepConfig[step.step] ?? stepConfig.default!;
                    const styles = statusStyles[step.status] ?? statusStyles.pending!;
                    const Icon = config.icon;
                    const isActive = step.step === currentStep;

                    return (
                        <div
                            key={step.step}
                            className={cn(
                                'flex items-center gap-3 px-3 py-2 rounded-lg transition-all',
                                styles.bg,
                                isActive && 'ring-1 ring-blue-200'
                            )}
                        >
                            {/* Icon */}
                            <div
                                className={cn(
                                    'w-8 h-8 rounded-full flex items-center justify-center',
                                    step.status === 'completed'
                                        ? 'bg-green-100'
                                        : step.status === 'failed'
                                            ? 'bg-red-100'
                                            : step.status === 'running'
                                                ? 'bg-blue-100'
                                                : 'bg-gray-100'
                                )}
                            >
                                {step.status === 'completed' ? (
                                    <Check className="h-4 w-4 text-green-600" />
                                ) : step.status === 'failed' ? (
                                    <AlertCircle className="h-4 w-4 text-red-600" />
                                ) : step.status === 'running' ? (
                                    <Icon className="h-4 w-4 text-blue-600 animate-pulse" />
                                ) : (
                                    <Icon className="h-4 w-4 text-gray-400" />
                                )}
                            </div>

                            {/* Content */}
                            <div className="flex-1">
                                <p className={cn('text-sm font-medium', styles.text)}>
                                    {config.label}
                                </p>
                                {step.message && (
                                    <p className="text-xs text-gray-500 mt-0.5">{step.message}</p>
                                )}
                            </div>

                            {/* Status badge */}
                            {step.status === 'running' && (
                                <span className="text-xs text-blue-500 animate-pulse">
                                    In progress...
                                </span>
                            )}
                        </div>
                    );
                })}
            </div>
        </motion.div>
    );
};

export default React.memo(TaskProgressCard);
