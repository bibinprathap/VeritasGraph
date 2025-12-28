/**
 * Reasoning Steps Timeline - Visual step-by-step reasoning trace
 */

import { useStore } from '../store';
import { motion } from 'framer-motion';
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  RotateCcw,
  Search,
  GitBranch,
  FileText,
  Sparkles,
  MessageSquare
} from 'lucide-react';

const ACTION_ICONS: Record<string, React.ReactNode> = {
  query_received: <MessageSquare className="w-4 h-4" />,
  entity_extraction: <Search className="w-4 h-4" />,
  relationship_traversal: <GitBranch className="w-4 h-4" />,
  source_retrieval: <FileText className="w-4 h-4" />,
  community_analysis: <Sparkles className="w-4 h-4" />,
  answer_generation: <Sparkles className="w-4 h-4" />,
};

const ACTION_COLORS: Record<string, string> = {
  query_received: '#FF6B6B',
  entity_extraction: '#4ECDC4',
  relationship_traversal: '#45B7D1',
  source_retrieval: '#FFEAA7',
  community_analysis: '#96CEB4',
  answer_generation: '#DDA0DD',
};

export default function ReasoningSteps() {
  const {
    currentResponse,
    currentStep,
    setCurrentStep,
    isAnimating,
    playAnimation,
    pauseAnimation,
    resetAnimation,
    nextStep,
    prevStep,
    setHighlightedNodes
  } = useStore();
  
  const steps = currentResponse?.reasoning_graph?.reasoning_steps || [];
  
  if (steps.length === 0) {
    return null;
  }
  
  const handleStepClick = (index: number) => {
    setCurrentStep(index);
    const step = steps[index];
    setHighlightedNodes(new Set(step.nodes_involved));
  };
  
  return (
    <div className="h-32 border-t border-white/10 bg-veritas-dark/80 backdrop-blur-sm flex flex-col">
      {/* Controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">Reasoning Trace</span>
          <span className="text-xs text-white/50">
            Step {currentStep + 1} of {steps.length}
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={resetAnimation}
            className="p-1.5 hover:bg-white/10 rounded text-white/60 hover:text-white transition-all"
            title="Reset"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className="p-1.5 hover:bg-white/10 rounded text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            title="Previous Step"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          <button
            onClick={isAnimating ? pauseAnimation : playAnimation}
            className="p-2 bg-veritas-primary/20 hover:bg-veritas-primary/30 rounded text-veritas-primary transition-all"
            title={isAnimating ? 'Pause' : 'Play'}
          >
            {isAnimating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={nextStep}
            disabled={currentStep === steps.length - 1}
            className="p-1.5 hover:bg-white/10 rounded text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            title="Next Step"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Timeline */}
      <div className="flex-1 overflow-x-auto px-4 py-3">
        <div className="flex items-start gap-2 min-w-max">
          {steps.map((step, index) => (
            <motion.button
              key={step.step_number}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => handleStepClick(index)}
              className={`relative flex flex-col items-center min-w-[120px] p-2 rounded-lg transition-all ${
                index === currentStep
                  ? 'bg-white/10 ring-2 ring-veritas-primary'
                  : index < currentStep
                  ? 'bg-white/5 opacity-60'
                  : 'bg-white/5 opacity-40 hover:opacity-60'
              }`}
            >
              {/* Icon */}
              <div 
                className="w-8 h-8 rounded-full flex items-center justify-center mb-1"
                style={{ 
                  backgroundColor: `${ACTION_COLORS[step.action] || '#888888'}22`,
                  color: ACTION_COLORS[step.action] || '#888888'
                }}
              >
                {ACTION_ICONS[step.action] || <Sparkles className="w-4 h-4" />}
              </div>
              
              {/* Label */}
              <span className="text-xs text-white/80 font-medium text-center">
                {step.action.replace(/_/g, ' ')}
              </span>
              
              {/* Nodes count */}
              {step.nodes_involved.length > 0 && (
                <span className="text-[10px] text-white/40 mt-0.5">
                  {step.nodes_involved.length} nodes
                </span>
              )}
              
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div 
                  className={`absolute top-6 left-full w-2 h-0.5 ${
                    index < currentStep ? 'bg-veritas-primary' : 'bg-white/20'
                  }`}
                />
              )}
              
              {/* Active indicator */}
              {index === currentStep && (
                <motion.div
                  layoutId="activeStep"
                  className="absolute -bottom-1 w-6 h-1 bg-veritas-primary rounded-full"
                />
              )}
            </motion.button>
          ))}
        </div>
      </div>
      
      {/* Current step description */}
      {steps[currentStep] && (
        <div className="px-4 pb-2">
          <p className="text-xs text-white/60 truncate">
            {steps[currentStep].description}
          </p>
        </div>
      )}
    </div>
  );
}
