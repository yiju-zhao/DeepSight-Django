import React, { useState } from "react";
import { Plus } from "lucide-react";

// Define the component props interface
interface CreateNotebookFormProps {
  onSubmit: (name: string, description: string) => Promise<{ success: boolean; error?: string }>;
  onCancel: () => void;
  loading: boolean;
  error?: string | null;
}

/**
 * Form component for creating new notebooks
 * Handles input validation and submission
 */
const CreateNotebookForm: React.FC<CreateNotebookFormProps> = ({
  onSubmit,
  onCancel,
  loading,
  error
}) => {
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!name.trim()) return;

    const result = await onSubmit(name, description);
    if (result.success) {
      setName("");
      setDescription("");
      onCancel(); // Close the form after successful creation
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Notebook Name *
          </label>
          <input
            type="text"
            placeholder="Enter notebook name"
            value={name}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
            disabled={loading}
            className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Description (Optional)
          </label>
          <textarea
            placeholder="Brief description"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
            disabled={loading}
            rows={3}
            className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all text-sm resize-none"
          />
        </div>
      </div>

      {error && (
        <div className="p-3 bg-accent-red-subtle border border-accent-red/20 rounded-lg">
          <p className="text-sm text-accent-red">{error}</p>
        </div>
      )}

      <div className="flex items-center justify-end space-x-3 pt-2">
        <button
          type="button"
          onClick={() => {
            onCancel();
            setName("");
            setDescription("");
          }}
          disabled={loading}
          className="px-6 py-2 border border-border text-gray-900 rounded-lg hover:bg-secondary transition-colors duration-300 font-medium text-sm disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading || !name.trim()}
          className="flex items-center space-x-2 px-6 py-2 bg-accent-red text-white rounded-lg hover:bg-accent-red-hover disabled:bg-gray-400 transition-colors duration-300 font-medium text-sm"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Creating...</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span>Create Notebook</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};

export default CreateNotebookForm;