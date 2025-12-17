/**
 * ChatErrorBoundary - Error Boundary for CopilotKit Chat
 *
 * Catches and handles errors in the chat interface to prevent full app crashes.
 * Provides user-friendly error messages and recovery options.
 *
 * Common Error Scenarios:
 * - Network connection failures to RAG agent server
 * - Authentication/session expiration
 * - RAG agent crashes or timeouts
 * - Invalid responses from backend
 *
 * Recovery Options:
 * - Retry connection
 * - Reload page
 * - Navigate back to dashboard
 */

import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  notebookId?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ChatErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chat Error Boundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });

    // Log to error tracking service if available
    if (window.analytics) {
      window.analytics.track('Chat Error', {
        error: error.message,
        stack: error.stack,
        notebookId: this.props.notebookId,
      });
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { error } = this.state;
      const isNetworkError = error?.message?.includes('network') ||
                            error?.message?.includes('fetch') ||
                            error?.message?.includes('ECONNREFUSED');
      const isAuthError = error?.message?.includes('401') ||
                         error?.message?.includes('unauthorized');

      return (
        <div className="h-full flex items-center justify-center bg-gray-50 p-6">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 space-y-4">
            {/* Error Icon */}
            <div className="flex justify-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
            </div>

            {/* Error Title */}
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Chat Error
              </h3>
              <p className="text-sm text-gray-600">
                {isNetworkError && 'Unable to connect to the research assistant server.'}
                {isAuthError && 'Your session has expired. Please log in again.'}
                {!isNetworkError && !isAuthError && 'Something went wrong with the chat interface.'}
              </p>
            </div>

            {/* Error Details (Development) */}
            {import.meta.env.DEV && error && (
              <div className="bg-gray-100 rounded p-3 text-xs font-mono text-gray-700 overflow-auto max-h-32">
                {error.toString()}
              </div>
            )}

            {/* Troubleshooting Tips */}
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <p className="text-sm text-blue-800 font-medium mb-2">
                Troubleshooting:
              </p>
              <ul className="text-xs text-blue-700 space-y-1">
                {isNetworkError && (
                  <>
                    <li>• Check if the RAG agent server is running (port 8101)</li>
                    <li>• Verify your network connection</li>
                    <li>• Check if CORS is configured correctly</li>
                  </>
                )}
                {isAuthError && (
                  <>
                    <li>• Your session may have expired</li>
                    <li>• Try logging in again</li>
                    <li>• Check if cookies are enabled</li>
                  </>
                )}
                {!isNetworkError && !isAuthError && (
                  <>
                    <li>• Try refreshing the page</li>
                    <li>• Clear browser cache and cookies</li>
                    <li>• Check browser console for details</li>
                  </>
                )}
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
              >
                Reload Page
              </button>
            </div>

            <button
              onClick={this.handleGoHome}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              <Home className="w-4 h-4" />
              Go to Dashboard
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChatErrorBoundary;
