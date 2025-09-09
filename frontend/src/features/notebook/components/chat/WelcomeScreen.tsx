import React from 'react';
import { MessageCircle, Sparkles, FileText, Brain, Zap, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import type { WelcomeScreenProps } from '@/features/notebook/types/chatSession';

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onStartChat,
  isCreating = false,
}) => {
  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Analysis',
      description: 'Advanced AI agent trained on your knowledge base for intelligent conversations',
    },
    {
      icon: FileText,
      title: 'Document-Aware',
      description: 'Chat about your uploaded documents with full context and understanding',
    },
    {
      icon: Sparkles,
      title: 'Smart Insights',
      description: 'Discover connections, patterns, and insights across your content',
    },
    {
      icon: Zap,
      title: 'Real-time Responses',
      description: 'Fast, streaming responses with source citations and references',
    },
  ];

  const quickStarters = [
    'Give me an overview of my knowledge base',
    'What are the key insights from my documents?',
    'How do these sources relate to each other?',
    'Help me explore a specific topic in depth',
  ];

  return (
    <div className="h-full flex items-center justify-center bg-gradient-to-br from-gray-50 to-white">
      <div className="max-w-4xl w-full px-8 py-12">
        {/* Main Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="w-24 h-24 bg-gradient-to-br from-red-100 via-rose-100 to-pink-100 rounded-3xl mx-auto mb-8 flex items-center justify-center shadow-lg"
          >
            <MessageCircle className="h-12 w-12 text-red-600" />
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-4xl font-bold text-gray-900 mb-4"
          >
            Start Your First Chat
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed"
          >
            Begin an intelligent conversation with your knowledge base. 
            Our AI agent will help you explore, analyze, and understand your content.
          </motion.p>

          {/* Start Chat Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Button
              onClick={onStartChat}
              disabled={isCreating}
              size="lg"
              className="px-8 py-4 text-lg bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.6 + (index * 0.1) }}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all duration-300 hover:border-red-200"
            >
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-gradient-to-br from-red-100 to-rose-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <feature.icon className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Quick Starters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
          className="text-center"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">
            Popular conversation starters
          </h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-4xl mx-auto">
            {quickStarters.map((starter, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: 1 + (index * 0.05) }}
              >
                <Badge
                  variant="secondary"
                  className="w-full p-3 text-sm text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-gray-300 cursor-default transition-colors duration-200 text-center"
                >
                  {starter}
                </Badge>
              </motion.div>
            ))}
          </div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 1.3 }}
            className="text-sm text-gray-500 mt-6"
          >
            Once you start your first chat, you can create multiple sessions using the "+" button
          </motion.p>
        </motion.div>
      </div>
    </div>
  );
};

export default WelcomeScreen;