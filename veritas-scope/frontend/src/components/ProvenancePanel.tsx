/**
 * Provenance Panel - Source document viewer with click-to-verify
 */

import { useState } from 'react';
import { useStore } from '../store';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  X, 
  ChevronRight, 
  ExternalLink,
  Copy,
  Check,
  BookOpen
} from 'lucide-react';

export default function ProvenancePanel() {
  const [copied, setCopied] = useState(false);
  
  const {
    currentResponse,
    selectedProvenance,
    setSelectedProvenance,
    selectedNode
  } = useStore();
  
  const provenance = currentResponse?.reasoning_graph?.provenance || [];
  
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  // Don't render if no response
  if (!currentResponse?.reasoning_graph) {
    return null;
  }
  
  return (
    <div className="w-[350px] flex-shrink-0 border-l border-white/10 flex flex-col bg-veritas-dark/50">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-veritas-secondary" />
          <span className="font-semibold text-white">Source Verification</span>
        </div>
        <p className="text-xs text-white/50 mt-1">
          Click nodes in the graph to see sources
        </p>
      </div>
      
      {/* Selected Source Detail */}
      <AnimatePresence>
        {selectedProvenance && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-b border-white/10"
          >
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-veritas-secondary">
                  Selected Source
                </span>
                <button
                  onClick={() => setSelectedProvenance(null)}
                  className="p-1 hover:bg-white/10 rounded transition-all"
                >
                  <X className="w-4 h-4 text-white/50" />
                </button>
              </div>
              
              <div className="bg-black/30 rounded-lg p-3 source-highlight">
                <p className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
                  {selectedProvenance.source_text}
                </p>
              </div>
              
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => handleCopy(selectedProvenance.source_text)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded text-xs text-white/70 transition-all"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-green-400" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      Copy
                    </>
                  )}
                </button>
                
                {selectedProvenance.relevance_score && (
                  <span className="text-xs text-white/50">
                    Relevance: {(selectedProvenance.relevance_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* All Sources List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <p className="text-xs text-white/50 mb-3 uppercase tracking-wide">
            All Sources ({provenance.length})
          </p>
          
          {provenance.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-8 h-8 text-white/20 mx-auto mb-2" />
              <p className="text-sm text-white/40">
                No source documents found
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {provenance.map((source, index) => (
                <motion.button
                  key={source.source_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => setSelectedProvenance(source)}
                  className={`w-full text-left p-3 rounded-lg transition-all ${
                    selectedProvenance?.source_id === source.source_id
                      ? 'bg-veritas-primary/20 border border-veritas-primary/50'
                      : 'bg-white/5 hover:bg-white/10 border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-veritas-secondary font-medium">
                      {source.source_type.toUpperCase()}
                    </span>
                    <ChevronRight className="w-4 h-4 text-white/30" />
                  </div>
                  <p className="text-sm text-white/80 line-clamp-2">
                    {source.source_text.substring(0, 100)}...
                  </p>
                  {source.relevance_score && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-veritas-primary rounded-full"
                          style={{ width: `${source.relevance_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-white/50">
                        {(source.relevance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </motion.button>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Selected Node Context */}
      {selectedNode && selectedNode.type !== 'text_unit' && (
        <div className="p-4 border-t border-white/10 bg-black/20">
          <p className="text-xs text-white/50 mb-2">Selected Node</p>
          <div className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ 
                backgroundColor: 
                  selectedNode.type === 'entity' ? '#4ECDC4' :
                  selectedNode.type === 'query' ? '#FF6B6B' :
                  selectedNode.type === 'answer' ? '#DDA0DD' :
                  '#888888'
              }}
            />
            <span className="text-sm text-white font-medium truncate">
              {selectedNode.label}
            </span>
          </div>
          {selectedNode.description && (
            <p className="text-xs text-white/60 mt-2 line-clamp-3">
              {selectedNode.description}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
