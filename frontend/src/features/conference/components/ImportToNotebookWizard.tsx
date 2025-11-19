import React, { useState, useEffect } from 'react';
import { X, FolderPlus, FolderOpen, Loader2, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { conferenceService } from '../services/ConferenceService';
import { notebooksApi } from '@/features/notebook/api';
import type { Notebook } from '@/shared/types/notebook';
import type { ImportResponse } from '../types';

interface ImportToNotebookWizardProps {
  isOpen: boolean;
  onClose: () => void;
  selectedPublicationIds: string[];
  onImportComplete?: (response: ImportResponse) => void;
}

type WizardStep = 'select-action' | 'choose-notebook' | 'create-notebook' | 'importing' | 'complete';
type Action = 'add' | 'create';

export const ImportToNotebookWizard: React.FC<ImportToNotebookWizardProps> = ({
  isOpen,
  onClose,
  selectedPublicationIds,
  onImportComplete,
}) => {
  const [step, setStep] = useState<WizardStep>('select-action');
  const [action, setAction] = useState<Action>('add');
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedNotebookId, setSelectedNotebookId] = useState<string>('');
  const [newNotebookName, setNewNotebookName] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [importResponse, setImportResponse] = useState<ImportResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Fetch notebooks when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchNotebooks();
    } else {
      // Reset state when modal closes
      resetWizard();
    }
  }, [isOpen]);

  const fetchNotebooks = async () => {
    try {
      setLoading(true);
      let allNotebooks: Notebook[] = [];
      let page = 1;
      let hasMore = true;

      // Fetch all pages of notebooks
      while (hasMore) {
        const response = await notebooksApi.getAll({ page, pageSize: 100 });

        // Standard DRF pagination format
        const notebooks = Array.isArray(response) ? response : (response as any)?.results || [];
        allNotebooks = [...allNotebooks, ...notebooks];

        // Check if there are more pages using next link
        const hasNextPage = (response as any)?.next !== null && (response as any)?.next !== undefined;
        hasMore = hasNextPage === true;
        page++;

        // Safety check: prevent infinite loop if something goes wrong
        if (page > 100) {
          console.warn('Stopped fetching notebooks after 100 pages (10,000 notebooks)');
          break;
        }
      }

      setNotebooks(allNotebooks);
      setError('');
    } catch (err: any) {
      setError('Failed to load notebooks');
      console.error('Error fetching notebooks:', err);
    } finally {
      setLoading(false);
    }
  };

  const resetWizard = () => {
    setStep('select-action');
    setAction('add');
    setSelectedNotebookId('');
    setNewNotebookName('');
    setSearchQuery('');
    setError('');
    setImportResponse(null);
  };

  const handleActionSelection = (selectedAction: Action) => {
    setAction(selectedAction);
    if (selectedAction === 'add') {
      setStep('choose-notebook');
    } else {
      setStep('create-notebook');
    }
  };

  const handleImport = async () => {
    setError('');
    setLoading(true);
    setStep('importing');

    try {
      const request =
        action === 'add'
          ? {
            publication_ids: selectedPublicationIds,
            action: 'add' as const,
            notebook_id: selectedNotebookId,
          }
          : {
            publication_ids: selectedPublicationIds,
            action: 'create' as const,
            notebook_name: newNotebookName.trim(),
          };

      const response = await conferenceService.importToNotebook(request);
      setImportResponse(response);
      setStep('complete');

      if (onImportComplete) {
        onImportComplete(response);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to import publications');
      setStep(action === 'add' ? 'choose-notebook' : 'create-notebook');
    } finally {
      setLoading(false);
    }
  };

  const filteredNotebooks = notebooks.filter((notebook) =>
    notebook.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const canProceed = () => {
    if (action === 'add') {
      return selectedNotebookId !== '';
    } else {
      return newNotebookName.trim() !== '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            Import to Notebook
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: Select Action */}
          {step === 'select-action' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-6">
                You have selected {selectedPublicationIds.length} publication
                {selectedPublicationIds.length > 1 ? 's' : ''}. Choose how to import them:
              </p>

              <button
                onClick={() => handleActionSelection('add')}
                className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
              >
                <div className="flex items-start space-x-4">
                  <FolderOpen className="text-gray-400 group-hover:text-blue-500 transition-colors" size={32} />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-1">
                      Add to Existing Notebook
                    </h3>
                    <p className="text-sm text-gray-600">
                      Select an existing notebook to add these publications to
                    </p>
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleActionSelection('create')}
                className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left group"
              >
                <div className="flex items-start space-x-4">
                  <FolderPlus className="text-gray-400 group-hover:text-green-500 transition-colors" size={32} />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-1">
                      Create New Notebook
                    </h3>
                    <p className="text-sm text-gray-600">
                      Create a new notebook and import publications into it
                    </p>
                  </div>
                </div>
              </button>
            </div>
          )}

          {/* Step 2a: Choose Existing Notebook */}
          {step === 'choose-notebook' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Notebook
                </label>
                <input
                  type="text"
                  placeholder="Search notebooks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="animate-spin text-gray-400" size={32} />
                  </div>
                ) : filteredNotebooks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    No notebooks found
                  </div>
                ) : (
                  filteredNotebooks.map((notebook) => (
                    <button
                      key={notebook.id}
                      onClick={() => setSelectedNotebookId(notebook.id)}
                      className={`w-full p-4 text-left hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0 ${selectedNotebookId === notebook.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                        }`}
                    >
                      <div className="font-medium text-gray-900">{notebook.name}</div>
                      {notebook.description && (
                        <div className="text-sm text-gray-600 mt-1">{notebook.description}</div>
                      )}
                    </button>
                  ))
                )}
              </div>

              {error && (
                <div className="flex items-center space-x-2 text-red-600 text-sm">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
            </div>
          )}

          {/* Step 2b: Create New Notebook */}
          {step === 'create-notebook' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notebook Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="Enter notebook name..."
                  value={newNotebookName}
                  onChange={(e) => setNewNotebookName(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  autoFocus
                />
              </div>

              {error && (
                <div className="flex items-center space-x-2 text-red-600 text-sm">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Importing */}
          {step === 'importing' && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <Loader2 className="animate-spin text-blue-500" size={48} />
              <p className="text-gray-600">Importing publications...</p>
            </div>
          )}

          {/* Step 4: Complete */}
          {step === 'complete' && importResponse && (
            <div className="space-y-6">
              <div className="flex items-center space-x-3">
                {importResponse.success ? (
                  <CheckCircle className="text-green-500" size={48} />
                ) : (
                  <AlertCircle className="text-yellow-500" size={48} />
                )}
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    {importResponse.success ? 'Import Successful!' : 'Import Completed with Issues'}
                  </h3>
                  <p className="text-sm text-gray-600">{importResponse.message}</p>
                </div>
              </div>

              {/* Summary */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total requested:</span>
                  <span className="font-medium">{importResponse.total_requested}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-green-600">Imported:</span>
                  <span className="font-medium text-green-600">{importResponse.imported}</span>
                </div>
                {importResponse.failed > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-red-600">Failed:</span>
                    <span className="font-medium text-red-600">{importResponse.failed}</span>
                  </div>
                )}
                {importResponse.skipped > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-yellow-600">Skipped:</span>
                    <span className="font-medium text-yellow-600">{importResponse.skipped}</span>
                  </div>
                )}
              </div>

              {/* Skipped Details */}
              {(importResponse.skipped_no_url.length > 0 || importResponse.skipped_duplicate.length > 0) && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700">Skipped Publications:</h4>
                  <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg">
                    {importResponse.skipped_no_url.map((item, index) => (
                      <div key={index} className="p-3 border-b border-gray-100 last:border-b-0">
                        <div className="text-sm font-medium text-gray-900">{item.title}</div>
                        <div className="text-xs text-gray-500 mt-1">{item.reason}</div>
                      </div>
                    ))}
                    {importResponse.skipped_duplicate.map((item, index) => (
                      <div key={index} className="p-3 border-b border-gray-100 last:border-b-0">
                        <div className="text-sm font-medium text-gray-900">{item.title}</div>
                        <div className="text-xs text-gray-500 mt-1">{item.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Appended to Batch Info */}
              {importResponse.appended_to_batch && (
                <div className="flex items-start space-x-2 bg-blue-50 rounded-lg p-3">
                  <Info className="text-blue-500 flex-shrink-0" size={16} />
                  <p className="text-sm text-blue-700">
                    Publications were added to an existing import batch for this notebook.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <button
            onClick={() => {
              if (step === 'choose-notebook' || step === 'create-notebook') {
                setStep('select-action');
              } else if (step === 'complete') {
                onClose();
              } else {
                onClose();
              }
            }}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            {step === 'complete' ? 'Close' : step === 'select-action' ? 'Cancel' : 'Back'}
          </button>

          {(step === 'choose-notebook' || step === 'create-notebook') && (
            <button
              onClick={handleImport}
              disabled={!canProceed() || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Importing...' : 'Import'}
            </button>
          )}

          {step === 'complete' && importResponse?.notebook_id && (
            <a
              href={`/deepdive/${importResponse.notebook_id}`}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              onClick={onClose}
            >
              Go to Notebook
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
