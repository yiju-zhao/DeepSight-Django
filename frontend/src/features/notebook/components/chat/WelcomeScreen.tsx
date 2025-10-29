import React from 'react';
import { MessageCircle, Loader2, AlertCircle, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import type { WelcomeScreenProps } from '@/features/notebook/type';

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onStartChat,
  isCreating = false,
  hasFiles = false,
}) => {
  return (
    <div className="h-full flex items-center justify-center bg-white">
      <div className="max-w-xl w-full px-8 py-12">
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >


          {/* Source Requirement Alert */}
          {!hasFiles && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mb-8 mx-auto max-w-md"
            >
              <Alert className="border border-amber-200 bg-amber-50/50">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <AlertDescription className="text-sm text-amber-900 leading-relaxed">
                      Add at least one source to your notebook before starting the conversation
                    </AlertDescription>
                  </div>
                </div>
              </Alert>
            </motion.div>
          )}

          {/* Start Chat Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: hasFiles ? 0.3 : 0.4 }}
          >
            <Button
              onClick={onStartChat}
              disabled={isCreating || !hasFiles}
              size="lg"
              className={`px-10 py-6 text-base font-medium rounded-xl transition-all duration-300 ${
                hasFiles && !isCreating
                  ? 'bg-red-600 hover:bg-red-700 text-white shadow-md hover:shadow-lg'
                  : 'bg-gray-200 hover:bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-2.5 h-5 w-5 animate-spin" />
                  Creating Session...
                </>
              ) : (
                <>
                  <MessageCircle className="mr-2.5 h-5 w-5" />
                  Start Conversation
                </>
              )}
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default WelcomeScreen;
