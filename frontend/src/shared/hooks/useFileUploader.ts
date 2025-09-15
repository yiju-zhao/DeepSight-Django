/**
 * Custom hook for file upload operations
 * Encapsulates file upload logic, validation, progress tracking, and error handling
 */

import { useState, useCallback } from 'react';
import { notifications } from '@/shared/utils/notifications';

export interface FileUploadOptions {
  maxFileSize?: number; // in MB
  allowedTypes?: string[];
  maxFiles?: number;
  onProgress?: (progress: number) => void;
  onSuccess?: (files: UploadedFile[]) => void;
  onError?: (error: string) => void;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  error?: string;
}

export interface FileUploadState {
  files: UploadedFile[];
  isUploading: boolean;
  uploadProgress: number;
  errors: string[];
}

const DEFAULT_OPTIONS: Required<FileUploadOptions> = {
  maxFileSize: 10, // 10MB
  allowedTypes: ['image/*', 'application/pdf', '.txt', '.md', '.doc', '.docx'],
  maxFiles: 5,
  onProgress: () => {},
  onSuccess: () => {},
  onError: () => {},
};

export function useFileUploader(options: FileUploadOptions = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };

  const [state, setState] = useState<FileUploadState>({
    files: [],
    isUploading: false,
    uploadProgress: 0,
    errors: [],
  });

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > config.maxFileSize * 1024 * 1024) {
      return `File "${file.name}" is too large. Maximum size is ${config.maxFileSize}MB.`;
    }

    // Check file type
    const isValidType = config.allowedTypes.some(type => {
      if (type.startsWith('.')) {
        return file.name.toLowerCase().endsWith(type.toLowerCase());
      }
      if (type.includes('*')) {
        const baseType = type.split('/')[0];
        return file.type.startsWith(baseType);
      }
      return file.type === type;
    });

    if (!isValidType) {
      return `File type "${file.type}" is not allowed.`;
    }

    return null;
  }, [config.maxFileSize, config.allowedTypes]);

  const validateFiles = useCallback((files: FileList): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    // Check total number of files
    if (files.length > config.maxFiles) {
      errors.push(`Maximum ${config.maxFiles} files are allowed.`);
      return { valid, errors };
    }

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const error = validateFile(file);

      if (error) {
        errors.push(error);
      } else {
        valid.push(file);
      }
    }

    return { valid, errors };
  }, [config.maxFiles, validateFile]);

  const addFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const { valid, errors } = validateFiles(fileArray as any);

    setState(prev => {
      const newFiles: UploadedFile[] = valid.map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'pending',
        progress: 0,
      }));

      return {
        ...prev,
        files: [...prev.files, ...newFiles],
        errors: [...prev.errors, ...errors],
      };
    });

    if (errors.length > 0) {
      errors.forEach(error => notifications.error.validation(error));
    }

    return valid;
  }, [validateFiles]);

  const removeFile = useCallback((fileId: string) => {
    setState(prev => ({
      ...prev,
      files: prev.files.filter(file => file.id !== fileId),
    }));
  }, []);

  const clearFiles = useCallback(() => {
    setState(prev => ({
      ...prev,
      files: [],
      errors: [],
    }));
  }, []);

  const clearErrors = useCallback(() => {
    setState(prev => ({
      ...prev,
      errors: [],
    }));
  }, []);

  const updateFileStatus = useCallback((fileId: string, updates: Partial<UploadedFile>) => {
    setState(prev => ({
      ...prev,
      files: prev.files.map(file =>
        file.id === fileId ? { ...file, ...updates } : file
      ),
    }));
  }, []);

  const simulateUpload = useCallback(async (fileId: string) => {
    updateFileStatus(fileId, { status: 'uploading', progress: 0 });

    // Simulate upload progress
    for (let progress = 0; progress <= 100; progress += 10) {
      await new Promise(resolve => setTimeout(resolve, 100));
      updateFileStatus(fileId, { progress });

      if (progress === 100) {
        updateFileStatus(fileId, {
          status: 'completed',
          url: `https://example.com/files/${fileId}`
        });
      }
    }
  }, [updateFileStatus]);

  const uploadFiles = useCallback(async (uploadFn?: (file: File) => Promise<any>) => {
    const pendingFiles = state.files.filter(file => file.status === 'pending');

    if (pendingFiles.length === 0) {
      notifications.error.validation('No files to upload');
      return;
    }

    setState(prev => ({ ...prev, isUploading: true }));

    try {
      for (const file of pendingFiles) {
        if (uploadFn) {
          updateFileStatus(file.id, { status: 'uploading' });
          // Custom upload function would be called here
          // const result = await uploadFn(file);
          updateFileStatus(file.id, { status: 'completed' });
        } else {
          // Fallback to simulation
          await simulateUpload(file.id);
        }
      }

      notifications.success.imported(pendingFiles.length, 'file');
      config.onSuccess(state.files.filter(f => f.status === 'completed'));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      notifications.error.generic(errorMessage);
      config.onError(errorMessage);
    } finally {
      setState(prev => ({ ...prev, isUploading: false }));
    }
  }, [state.files, config, simulateUpload, updateFileStatus]);

  const getFilesByStatus = useCallback((status: UploadedFile['status']) => {
    return state.files.filter(file => file.status === status);
  }, [state.files]);

  const getTotalProgress = useCallback(() => {
    if (state.files.length === 0) return 0;
    const totalProgress = state.files.reduce((sum, file) => sum + file.progress, 0);
    return Math.round(totalProgress / state.files.length);
  }, [state.files]);

  return {
    // State
    files: state.files,
    isUploading: state.isUploading,
    errors: state.errors,

    // Computed values
    totalProgress: getTotalProgress(),
    pendingFiles: getFilesByStatus('pending'),
    uploadingFiles: getFilesByStatus('uploading'),
    completedFiles: getFilesByStatus('completed'),
    errorFiles: getFilesByStatus('error'),

    // Actions
    addFiles,
    removeFile,
    clearFiles,
    clearErrors,
    uploadFiles,
    updateFileStatus,

    // Utilities
    validateFile,
    getFilesByStatus,
  };
}