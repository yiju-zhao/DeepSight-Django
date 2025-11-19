import React, { useState, useEffect } from 'react';
import { Settings, X, MessageSquare, Palette } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { COLORS } from "@/features/notebook/config/uiConfig";
import { useNotebookSettings } from '@/features/notebook/contexts/NotebookSettingsContext';
import { useModelsQuery, useSelectModelMutation } from '@/features/notebook/hooks/chat/useSessionQueries';
import { useToast } from "@/shared/components/ui/use-toast";

interface NotebookSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    notebookId: string;
}

const NotebookSettingsModal: React.FC<NotebookSettingsModalProps> = ({
    isOpen,
    onClose,
    notebookId
}) => {
    const { toast } = useToast();
    const [activeTab, setActiveTab] = useState<'chat' | 'studio'>('chat');

    // Context Data
    const {
        reportConfig,
        podcastConfig,
        updateReportConfig,
        updatePodcastConfig
    } = useNotebookSettings();

    // Chat Data
    const modelsQuery = useModelsQuery(notebookId);
    const selectModelMutation = useSelectModelMutation(notebookId);
    const availableModels = modelsQuery.data?.available_models || [];
    const currentModel = modelsQuery.data?.current_model || '';

    // Local state for Studio settings (to support Save/Cancel pattern)
    const [localReportConfig, setLocalReportConfig] = useState(reportConfig);
    const [localPodcastConfig, setLocalPodcastConfig] = useState(podcastConfig);

    // Xinference models state
    const [xinferenceModels, setXinferenceModels] = useState<any[]>([]);
    const [loadingXinferenceModels, setLoadingXinferenceModels] = useState(false);

    // Sync local state when modal opens
    useEffect(() => {
        if (isOpen) {
            setLocalReportConfig(reportConfig);
            setLocalPodcastConfig(podcastConfig);
            fetchXinferenceModels();
        }
    }, [isOpen, reportConfig, podcastConfig]);

    const fetchXinferenceModels = async () => {
        setLoadingXinferenceModels(true);
        try {
            const response = await fetch('/api/v1/reports/xinference/models/');
            const data = await response.json();
            setXinferenceModels(data.models || []);
        } catch (error) {
            console.error('Failed to fetch Xinference models:', error);
            setXinferenceModels([]);
        } finally {
            setLoadingXinferenceModels(false);
        }
    };

    // Handlers
    const handleReportConfigChange = (updates: Partial<typeof reportConfig>) => {
        setLocalReportConfig(prev => ({ ...prev, ...updates }));
    };

    const handlePodcastConfigChange = (updates: Partial<typeof podcastConfig>) => {
        setLocalPodcastConfig(prev => ({ ...prev, ...updates }));
    };

    const handleChatModelChange = async (model: string) => {
        try {
            await selectModelMutation.mutateAsync(model);
            toast({
                title: 'Model Updated',
                description: `Chat model changed to ${model}`,
            });
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to update chat model',
                variant: 'destructive',
            });
        }
    };

    const handleSave = () => {
        updateReportConfig(localReportConfig);
        updatePodcastConfig(localPodcastConfig);
        onClose();
        toast({
            title: 'Settings Saved',
            description: 'Studio settings have been updated',
        });
    };

    if (!isOpen) return null;

    const formatModelName = (value: string): string => {
        return value.charAt(0).toUpperCase() + value.slice(1);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b">
                <div className="flex items-center space-x-2">
                    <Settings className="h-5 w-5 text-gray-600" />
                    <h2 className="text-lg font-semibold text-gray-900">Notebook Settings</h2>
                </div>
                <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                    <X className="h-5 w-5" />
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b px-6">
                <button
                    className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'chat'
                            ? 'border-red-600 text-red-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    onClick={() => setActiveTab('chat')}
                >
                    <div className="flex items-center space-x-2">
                        <MessageSquare className="h-4 w-4" />
                        <span>Chat Settings</span>
                    </div>
                </button>
                <button
                    className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'studio'
                            ? 'border-red-600 text-red-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    onClick={() => setActiveTab('studio')}
                >
                    <div className="flex items-center space-x-2">
                        <Palette className="h-4 w-4" />
                        <span>Studio Settings</span>
                    </div>
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'chat' && (
                    <div className="space-y-6 max-w-2xl">
                        <div className="space-y-4">
                            <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Model Configuration</h3>
                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-gray-700">Chat Model</label>
                                <select
                                    className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                    value={currentModel}
                                    onChange={(e) => handleChatModelChange(e.target.value)}
                                    disabled={selectModelMutation.isPending}
                                >
                                    {availableModels.map((model: string) => (
                                        <option key={model} value={model}>
                                            {model}
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500">
                                    Select the AI model to use for chat sessions.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'studio' && (
                    <div className="space-y-8 max-w-3xl">
                        {/* Report Settings */}
                        <div className="space-y-4">
                            <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Report Generation</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">AI Model Provider</label>
                                    <select
                                        className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                        value={localReportConfig.model_provider || ''}
                                        onChange={(e) => handleReportConfigChange({ model_provider: e.target.value, model_uid: undefined })}
                                    >
                                        <option value="openai">OpenAI</option>
                                        <option value="xinference">Xinference</option>
                                        {/* Add other providers if available in availableModels */}
                                    </select>
                                </div>

                                {localReportConfig.model_provider === 'xinference' && (
                                    <div className="space-y-2">
                                        <label className="block text-sm font-medium text-gray-700">Xinference Model</label>
                                        {loadingXinferenceModels ? (
                                            <div className="text-sm text-gray-500 p-3 border rounded-lg">Loading...</div>
                                        ) : (
                                            <select
                                                className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                                value={localReportConfig.model_uid || ''}
                                                onChange={(e) => handleReportConfigChange({ model_uid: e.target.value })}
                                            >
                                                <option value="">Select a model</option>
                                                {xinferenceModels.map(model => (
                                                    <option key={model.uid} value={model.uid}>{model.display_name || model.name}</option>
                                                ))}
                                            </select>
                                        )}
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">Search Engine</label>
                                    <select
                                        className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                        value={localReportConfig.retriever || 'tavily'}
                                        onChange={(e) => handleReportConfigChange({ retriever: e.target.value })}
                                    >
                                        <option value="searxng">SearXNG</option>
                                        <option value="tavily">Tavily</option>
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">Time Range</label>
                                    <select
                                        className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                        value={localReportConfig.time_range || 'ALL'}
                                        onChange={(e) => handleReportConfigChange({ time_range: e.target.value })}
                                    >
                                        <option value="ALL">All Time</option>
                                        <option value="day">Last 24 Hours</option>
                                        <option value="week">Last 7 Days</option>
                                        <option value="month">Last 30 Days</option>
                                        <option value="year">Last Year</option>
                                    </select>
                                </div>
                            </div>

                            <div className="flex flex-col space-y-3 pt-2">
                                {localReportConfig.retriever === 'tavily' && (
                                    <div className="flex items-center space-x-2">
                                        <input
                                            type="checkbox"
                                            id="white-domain"
                                            className="h-4 w-4 accent-red-500 border-gray-300 rounded"
                                            checked={localReportConfig.include_domains || false}
                                            onChange={(e) => handleReportConfigChange({ include_domains: e.target.checked })}
                                        />
                                        <label htmlFor="white-domain" className="text-sm text-gray-700">Include Whitelist Domains</label>
                                    </div>
                                )}
                                <div className="flex items-center space-x-2">
                                    <input
                                        type="checkbox"
                                        id="include-image"
                                        className="h-4 w-4 accent-red-500 border-gray-300 rounded"
                                        checked={localReportConfig.include_image || false}
                                        onChange={(e) => handleReportConfigChange({ include_image: e.target.checked })}
                                    />
                                    <label htmlFor="include-image" className="text-sm text-gray-700">Include Images in Report</label>
                                </div>
                            </div>
                        </div>

                        {/* Podcast Settings */}
                        <div className="space-y-4">
                            <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Podcast Generation</h3>
                            <div className="space-y-2 max-w-md">
                                <label className="block text-sm font-medium text-gray-700">Language</label>
                                <select
                                    className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                                    value={localPodcastConfig.language || 'en'}
                                    onChange={(e) => handlePodcastConfigChange({ language: e.target.value })}
                                >
                                    <option value="en">English</option>
                                    <option value="zh">Chinese (中文)</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Footer (Only for Studio tab since Chat saves immediately) */}
            {activeTab === 'studio' && (
                <div className="flex justify-end space-x-3 px-6 py-4 border-t bg-gray-50">
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button
                        onClick={handleSave}
                        className={`${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`}
                    >
                        Save Changes
                    </Button>
                </div>
            )}
        </div>
    );
};

export default NotebookSettingsModal;
