import React from 'react';
import { MessageCircle, Loader2, AlertCircle, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import type { WelcomeScreenProps } from '@/features/notebook/types/chatSession';

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onStartChat,
  isCreating = false,
  hasFiles = false,
}) => {
  return (
    <div className="h-full flex items-center justify-center bg-gradient-to-br from-gray-50 to-white">
      <div className="max-w-lg w-full px-8 py-12">
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          {/* Icon */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="w-20 h-20 bg-gradient-to-br from-red-100 via-rose-100 to-pink-100 rounded-3xl mx-auto mb-8 flex items-center justify-center shadow-lg"
          >
            <MessageCircle className="h-10 w-10 text-red-600" />
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-3xl font-bold text-gray-900 mb-6"
          >
            Start Your Chat
          </motion.h1>

          {/* Source Requirement Alert */}
          {!hasFiles && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mb-8"
            >
              <Alert className="border-amber-200 bg-amber-50">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <AlertDescription className="text-amber-800">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 flex-shrink-0" />
                    <span>Add at least one source to your notebook before starting the conversation</span>
                  </div>
                </AlertDescription>
              </Alert>
            </motion.div>
          )}

          {/* Start Chat Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: hasFiles ? 0.3 : 0.4 }}
          >
            <Button
              onClick={onStartChat}
              disabled={isCreating || !hasFiles}
              size="lg"
              className={`px-8 py-4 text-lg rounded-xl shadow-lg transition-all duration-300 transform ${
                hasFiles && !isCreating
                  ? 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white hover:shadow-xl hover:scale-105'
                  : 'bg-gray-400 hover:bg-gray-400 text-white cursor-not-allowed opacity-60'
              }`}
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                  Creating Session...
                </>
              ) : (
                <>
                  <MessageCircle className="mr-3 h-5 w-5" />
                  Start Chat
                </>
              )}
            </Button>
          </motion.div>

          {/* Helper Text */}
          {hasFiles && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="text-sm text-gray-500 mt-6"
            >
              Begin an intelligent conversation with your knowledge base
            </motion.p>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default WelcomeScreen;