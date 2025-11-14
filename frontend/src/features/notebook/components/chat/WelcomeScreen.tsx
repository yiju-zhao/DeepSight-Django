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
      <div className="max-w-xl w-full px-6 md:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="bg-white border border-[#E3E3E3] rounded-2xl shadow-[rgba(0,0,0,0.04)_0px_4px_8px] px-6 py-8 md:px-8 md:py-10"
        >
          {/* Icon + Title */}
          <div className="flex items-center gap-4 mb-6">
            <div className="w-10 h-10 rounded-full bg-[#F5F5F5] flex items-center justify-center">
              <MessageCircle className="h-5 w-5 text-[#7F7F7F]" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] uppercase tracking-[0.3px] text-[#7B7B7B]">
                DeepDive Chat
              </span>
              <h2 className="text-[20px] md:text-[22px] font-bold text-[#1E1E1E] leading-tight mt-0.5">
                Start a conversation
              </h2>
              <p className="text-sm text-[#666666] mt-1">
                Ask questions about your sources and explore insights with the AI co-pilot.
              </p>
            </div>
          </div>

          {!hasFiles && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mb-6"
            >
              <Alert className="border border-amber-200 bg-amber-50/60">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-4 w-4 text-amber-700 flex-shrink-0 mt-0.5" />
                  <AlertDescription className="text-xs text-amber-900 leading-relaxed">
                    Add at least one source to this notebook before starting a conversation.
                  </AlertDescription>
                </div>
              </Alert>
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: hasFiles ? 0.3 : 0.4 }}
            className="mt-4"
          >
            <Button
              onClick={onStartChat}
              disabled={isCreating || !hasFiles}
              size="lg"
              className={`px-8 py-4 text-sm font-medium rounded-lg transition-all duration-300 ${
                hasFiles && !isCreating
                  ? 'bg-black hover:bg-black/80 text-white shadow-[rgba(0,0,0,0.08)_0px_8px_12px] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px]'
                  : 'bg-[#F5F5F5] hover:bg-[#F5F5F5] text-[#B1B1B1] cursor-not-allowed'
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
