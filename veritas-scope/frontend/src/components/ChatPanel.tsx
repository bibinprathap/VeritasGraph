/**
 * Chat Panel Component - Query input and response display
 */

import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { executeQuery } from '../api';
import { Send, Loader2, Sparkles, AlertCircle, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ChatPanel() {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const {
    query,
    setQuery,
    queryType,
    outputFolder,
    communityLevel,
    temperature,
    responseType,
    isLoading,
    setLoading,
    error,
    setError,
    setCurrentResponse,
    chatHistory,
    addChatMessage,
    clearChat,
    resetAnimation
  } = useStore();
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    
    const userQuery = inputValue.trim();
    setInputValue('');
    setQuery(userQuery);
    setError(null);
    resetAnimation();
    
    // Add user message
    addChatMessage({
      id: `user-${Date.now()}`,
      role: 'user',
      content: userQuery,
      timestamp: new Date()
    });
    
    setLoading(true);
    
    try {
      const response = await executeQuery({
        query: userQuery,
        query_type: queryType,
        output_folder: outputFolder,
        community_level: communityLevel,
        temperature,
        response_type: responseType,
        include_graph: true,
        animate_trace: true
      });
      
      setCurrentResponse(response);
      
      // Add assistant message
      addChatMessage({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        reasoningGraph: response.reasoning_graph
      });
      
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute query';
      setError(errorMessage);
      addChatMessage({
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date()
      });
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-veritas-primary" />
          <span className="font-semibold text-white">Ask VeritasGraph</span>
        </div>
        {chatHistory.length > 0 && (
          <button
            onClick={clearChat}
            className="p-1.5 text-white/50 hover:text-white/80 hover:bg-white/10 rounded transition-all"
            title="Clear chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatHistory.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-16 h-16 rounded-full bg-veritas-primary/20 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-veritas-primary" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Welcome to Veritas-Scope
            </h3>
            <p className="text-sm text-white/60 max-w-xs">
              Ask complex questions and watch the multi-hop reasoning unfold in real-time.
            </p>
            <div className="mt-6 space-y-2">
              <p className="text-xs text-white/40">Try asking:</p>
              {[
                "What are the main themes in this story?",
                "How do the characters relate to each other?",
                "Summarize the key events"
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => setInputValue(suggestion)}
                  className="block w-full text-left text-sm text-veritas-primary/80 hover:text-veritas-primary px-3 py-2 rounded bg-white/5 hover:bg-white/10 transition-all"
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          <AnimatePresence>
            {chatHistory.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-veritas-primary text-white rounded-br-md'
                      : 'bg-white/10 text-white/90 rounded-bl-md'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  {message.reasoningGraph && (
                    <div className="mt-2 pt-2 border-t border-white/20 flex items-center gap-2 text-xs text-white/60">
                      <span>{message.reasoningGraph.total_nodes} nodes</span>
                      <span>•</span>
                      <span>{message.reasoningGraph.total_hops} hops</span>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        
        {/* Loading indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-white/60"
          >
            <Loader2 className="w-4 h-4 animate-spin text-veritas-primary" />
            <span className="text-sm">Traversing knowledge graph...</span>
          </motion.div>
        )}
        
        {/* Error */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 p-3 bg-red-500/20 rounded-lg"
          >
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span className="text-sm text-red-300">{error}</span>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
        <div className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a complex question..."
            disabled={isLoading}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pr-12 text-white placeholder-white/40 focus:outline-none focus:border-veritas-primary transition-all"
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-veritas-primary rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-veritas-primary/80 transition-all"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
