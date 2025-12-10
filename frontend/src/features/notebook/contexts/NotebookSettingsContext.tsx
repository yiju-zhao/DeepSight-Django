import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Define config types (matching what was in useGenerationManager/StudioPanel)
export interface ReportConfig {
    topic?: string;
    article_title?: string;
    model_provider?: string;
    retriever?: string;
    prompt_type?: string;
    include_image?: boolean;
    include_domains?: boolean;
    time_range?: string;
    model?: string;
    [key: string]: any;
}

export interface PodcastConfig {
    title?: string;
    description?: string;
    topic?: string;
    language?: string;
    model?: string;
    [key: string]: any;
}

// Studio Mode Configuration
export interface StudioConfig {
    style: 'academic' | 'casual' | 'technical' | 'business';
    skip_clarification: boolean;
    max_research_iterations?: number;
    timeout?: number;
}

interface NotebookSettingsContextType {
    // Existing configs
    reportConfig: ReportConfig;
    podcastConfig: PodcastConfig;
    updateReportConfig: (updates: Partial<ReportConfig>) => void;
    updatePodcastConfig: (updates: Partial<PodcastConfig>) => void;

    // Studio Mode
    studioMode: boolean;
    setStudioMode: (enabled: boolean) => void;
    toggleStudioMode: () => void;
    studioConfig: StudioConfig;
    updateStudioConfig: (updates: Partial<StudioConfig>) => void;
}

export const DEFAULT_REPORT_CONFIG: ReportConfig = {
    topic: '',
    article_title: '',
    model_provider: 'openai',
    retriever: 'tavily',
    prompt_type: 'general',
    include_image: false,
    include_domains: false,
    time_range: 'ALL',
    model: 'gpt-4'
};

export const DEFAULT_PODCAST_CONFIG: PodcastConfig = {
    title: '',
    description: '',
    topic: '',
    language: 'en',
    model: 'gpt-4'
};

export const DEFAULT_STUDIO_CONFIG: StudioConfig = {
    style: 'academic',
    skip_clarification: false,
    max_research_iterations: 10,
    timeout: 600,
};

const NotebookSettingsContext = createContext<NotebookSettingsContextType | undefined>(undefined);

export const NotebookSettingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [reportConfig, setReportConfig] = useState<ReportConfig>(DEFAULT_REPORT_CONFIG);
    const [podcastConfig, setPodcastConfig] = useState<PodcastConfig>(DEFAULT_PODCAST_CONFIG);

    // Studio Mode state
    const [studioMode, setStudioMode] = useState<boolean>(false);
    const [studioConfig, setStudioConfig] = useState<StudioConfig>(DEFAULT_STUDIO_CONFIG);

    const updateReportConfig = useCallback((updates: Partial<ReportConfig>) => {
        setReportConfig(prev => ({ ...prev, ...updates }));
    }, []);

    const updatePodcastConfig = useCallback((updates: Partial<PodcastConfig>) => {
        setPodcastConfig(prev => ({ ...prev, ...updates }));
    }, []);

    const toggleStudioMode = useCallback(() => {
        setStudioMode(prev => !prev);
    }, []);

    const updateStudioConfig = useCallback((updates: Partial<StudioConfig>) => {
        setStudioConfig(prev => ({ ...prev, ...updates }));
    }, []);

    return (
        <NotebookSettingsContext.Provider
            value={{
                reportConfig,
                podcastConfig,
                updateReportConfig,
                updatePodcastConfig,
                studioMode,
                setStudioMode,
                toggleStudioMode,
                studioConfig,
                updateStudioConfig,
            }}
        >
            {children}
        </NotebookSettingsContext.Provider>
    );
};

export const useNotebookSettings = () => {
    const context = useContext(NotebookSettingsContext);
    if (context === undefined) {
        throw new Error('useNotebookSettings must be used within a NotebookSettingsProvider');
    }
    return context;
};

