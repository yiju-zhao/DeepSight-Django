import React, { useState, useEffect } from 'react';
import { Settings, X, MessageSquare, Palette, RotateCcw } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { COLORS } from "@/features/notebook/config/uiConfig";
import { useNotebookSettings, DEFAULT_REPORT_CONFIG, DEFAULT_PODCAST_CONFIG } from '@/features/notebook/contexts/NotebookSettingsContext';
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

    // Xinference models state
    const [xinferenceModels, setXinferenceModels] = useState<any[]>([]);
    const [loadingXinferenceModels, setLoadingXinferenceModels] = useState(false);

    // Fetch Xinference models when modal opens
    useEffect(() => {
        if (isOpen) {
            fetchXinferenceModels();
        }
    }, [isOpen]);

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
        updateReportConfig(updates);
    };

    const handlePodcastConfigChange = (updates: Partial<typeof podcastConfig>) => {
        updatePodcastConfig(updates);
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

    const handleReset = () => {
        if (activeTab === 'studio') {
            updateReportConfig(DEFAULT_REPORT_CONFIG);
            updatePodcastConfig(DEFAULT_PODCAST_CONFIG);
            toast({
                title: 'Settings Reset',
                description: 'Studio settings have been reset to defaults',
            });
        }
    };

    if (!isOpen) return null;

    const formatModelName = (value: string): string => {
        return value.charAt(0).toUpperCase() + value.slice(1);
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#F7F7F7]">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-[#F5F5F5] rounded-lg flex items-center justify-center">
                        <Settings className="h-5 w-5 text-[#1E1E1E]" />
                    </div>
                    <h2 className="text-[18px] font-bold text-[#1E1E1E]">Notebook Settings</h2>
                </div>
                <div className="flex items-center space-x-2">
                    {activeTab === 'studio' && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleReset}
                            className="h-8 px-3 text-[#666666] hover:text-[#CE0E2D] hover:bg-[#FEF2F2] rounded-lg transition-colors text-[13px] font-medium"
                        >
                            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                            Reset
                        </Button>
                    )}
                    <button
                        onClick={onClose}
                        className="h-8 w-8 flex items-center justify-center text-[#B1B1B1] hover:text-[#666666] hover:bg-[#F5F5F5] rounded-full transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[#F7F7F7] px-6">
                <button
                    className={`py-3 px-1 mr-6 text-[14px] font-medium border-b-2 transition-all ${activeTab === 'chat'
                        ? 'border-[#CE0E2D] text-[#CE0E2D]'
                        : 'border-transparent text-[#666666] hover:text-[#1E1E1E]'
                        }`}
                    onClick={() => setActiveTab('chat')}
                >
                    <div className="flex items-center space-x-2">
                        <MessageSquare className="h-4 w-4" />
                        <span>Chat Settings</span>
                    </div>
                </button>
                <button
                    className={`py-3 px-1 text-[14px] font-medium border-b-2 transition-all ${activeTab === 'studio'
                        ? 'border-[#CE0E2D] text-[#CE0E2D]'
                        : 'border-transparent text-[#666666] hover:text-[#1E1E1E]'
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
                    <div className="space-y-6 max-w-2xl animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className="space-y-4">
                            <h3 className="text-[15px] font-bold text-[#1E1E1E] border-b border-[#F7F7F7] pb-2">Model Configuration</h3>
                            <div className="space-y-2">
                                <label className="block text-[13px] font-medium text-[#1E1E1E]">Chat Model</label>
                                <div className="relative">
                                    <select
                                        className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
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
                                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                        <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </div>
                                </div>
                                <p className="text-[12px] text-[#999999]">
                                    Select the AI model to use for chat sessions.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'studio' && (
                    <div className="space-y-8 max-w-3xl animate-in fade-in slide-in-from-bottom-2 duration-300 pb-6">
                        {/* Report Settings */}
                        <div className="space-y-4">
                            <h3 className="text-[15px] font-bold text-[#1E1E1E] border-b border-[#F7F7F7] pb-2">Report Generation</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="block text-[13px] font-medium text-[#1E1E1E]">AI Model Provider</label>
                                    <div className="relative">
                                        <select
                                            className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                            value={reportConfig.model_provider || ''}
                                            onChange={(e) => handleReportConfigChange({ model_provider: e.target.value, model_uid: undefined })}
                                        >
                                            <option value="openai">OpenAI</option>
                                            <option value="xinference">Xinference</option>
                                        </select>
                                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                            <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                            </svg>
                                        </div>
                                    </div>
                                </div>

                                {reportConfig.model_provider === 'xinference' && (
                                    <div className="space-y-2">
                                        <label className="block text-[13px] font-medium text-[#1E1E1E]">Xinference Model</label>
                                        {loadingXinferenceModels ? (
                                            <div className="text-[14px] text-[#999999] p-2.5 border border-[#E3E3E3] rounded-xl bg-[#F9FAFB]">Loading...</div>
                                        ) : (
                                            <div className="relative">
                                                <select
                                                    className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                                    value={reportConfig.model_uid || ''}
                                                    onChange={(e) => handleReportConfigChange({ model_uid: e.target.value })}
                                                >
                                                    <option value="">Select a model</option>
                                                    {xinferenceModels.map(model => (
                                                        <option key={model.uid} value={model.uid}>{model.display_name || model.name}</option>
                                                    ))}
                                                </select>
                                                <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                                    <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                                    </svg>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <label className="block text-[13px] font-medium text-[#1E1E1E]">Search Engine</label>
                                    <div className="relative">
                                        <select
                                            className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                            value={reportConfig.retriever || 'tavily'}
                                            onChange={(e) => handleReportConfigChange({ retriever: e.target.value })}
                                        >
                                            <option value="searxng">SearXNG</option>
                                            <option value="tavily">Tavily</option>
                                        </select>
                                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                            <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                            </svg>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="block text-[13px] font-medium text-[#1E1E1E]">Time Range</label>
                                    <div className="relative">
                                        <select
                                            className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                            value={reportConfig.time_range || 'ALL'}
                                            onChange={(e) => handleReportConfigChange({ time_range: e.target.value })}
                                        >
                                            <option value="ALL">All Time</option>
                                            <option value="day">Last 24 Hours</option>
                                            <option value="week">Last 7 Days</option>
                                            <option value="month">Last 30 Days</option>
                                            <option value="year">Last Year</option>
                                        </select>
                                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                            <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                            </svg>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Report Template Selector */}
                            <div className="col-span-1 md:col-span-2 space-y-2">
                                <label className="block text-[13px] font-medium text-[#1E1E1E]">
                                    Report Template
                                </label>
                                <div className="relative">
                                    <select
                                        className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                        value={reportConfig.prompt_type || 'general'}
                                        onChange={(e) => handleReportConfigChange({ prompt_type: e.target.value })}
                                    >
                                        <option value="general">General</option>
                                        <option value="paper">Research Paper</option>
                                        <option value="financial">Financial Report</option>
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                        <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </div>
                                </div>
                                <p className="text-[12px] text-[#999999]">
                                    Choose the structure and style for your research report
                                </p>
                            </div>

                            <div className="flex flex-col space-y-3 pt-2">
                                {reportConfig.retriever === 'tavily' && (
                                    <div className="flex items-center space-x-3 p-3 bg-[#F9FAFB] rounded-xl border border-[#E3E3E3]">
                                        <input
                                            type="checkbox"
                                            id="white-domain"
                                            className="h-4 w-4 accent-[#CE0E2D] border-gray-300 rounded focus:ring-[#CE0E2D]"
                                            checked={reportConfig.include_domains || false}
                                            onChange={(e) => handleReportConfigChange({ include_domains: e.target.checked })}
                                        />
                                        <label htmlFor="white-domain" className="text-[13px] font-medium text-[#1E1E1E] cursor-pointer select-none">Include Whitelist Domains</label>
                                    </div>
                                )}
                                <div className="flex items-center space-x-3 p-3 bg-[#F9FAFB] rounded-xl border border-[#E3E3E3]">
                                    <input
                                        type="checkbox"
                                        id="include-image"
                                        className="h-4 w-4 accent-[#CE0E2D] border-gray-300 rounded focus:ring-[#CE0E2D]"
                                        checked={reportConfig.include_image || false}
                                        onChange={(e) => handleReportConfigChange({ include_image: e.target.checked })}
                                    />
                                    <label htmlFor="include-image" className="text-[13px] font-medium text-[#1E1E1E] cursor-pointer select-none">Include Images in Report</label>
                                </div>
                            </div>
                        </div>

                        {/* Podcast Settings */}
                        <div className="space-y-4">
                            <h3 className="text-[15px] font-bold text-[#1E1E1E] border-b border-[#F7F7F7] pb-2">Podcast Generation</h3>
                            <div className="space-y-2 max-w-md">
                                <label className="block text-[13px] font-medium text-[#1E1E1E]">Language</label>
                                <div className="relative">
                                    <select
                                        className="w-full p-2.5 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[14px] text-[#1E1E1E] appearance-none focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] transition-all"
                                        value={podcastConfig.language || 'en'}
                                        onChange={(e) => handlePodcastConfigChange({ language: e.target.value })}
                                    >
                                        <option value="en">English</option>
                                        <option value="zh">Chinese (中文)</option>
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                        <svg className="w-4 h-4 text-[#666666]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default NotebookSettingsModal;
