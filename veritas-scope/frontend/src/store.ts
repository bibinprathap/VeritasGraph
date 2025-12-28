/**
 * Zustand store for Veritas-Scope state management
 */

import { create } from 'zustand';
import type { 
  QueryResponse, 
  ReasoningTraceGraph, 
  GraphNode, 
  ReasoningStep,
  ProvenanceInfo 
} from './types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  reasoningGraph?: ReasoningTraceGraph;
}

interface VeritasScopeState {
  // Query state
  query: string;
  queryType: 'local' | 'global';
  outputFolder: string;
  communityLevel: number;
  temperature: number;
  responseType: string;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  
  // Results state
  currentResponse: QueryResponse | null;
  chatHistory: ChatMessage[];
  
  // Visualization state
  selectedNode: GraphNode | null;
  highlightedNodes: Set<string>;
  currentStep: number;
  isAnimating: boolean;
  showLabels: boolean;
  show3D: boolean;
  
  // Provenance panel
  selectedProvenance: ProvenanceInfo | null;
  
  // Available folders
  availableFolders: string[];
  
  // Actions
  setQuery: (query: string) => void;
  setQueryType: (type: 'local' | 'global') => void;
  setOutputFolder: (folder: string) => void;
  setCommunityLevel: (level: number) => void;
  setTemperature: (temp: number) => void;
  setResponseType: (type: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setCurrentResponse: (response: QueryResponse | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  clearChat: () => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setHighlightedNodes: (nodes: Set<string>) => void;
  setCurrentStep: (step: number) => void;
  setIsAnimating: (animating: boolean) => void;
  setShowLabels: (show: boolean) => void;
  setShow3D: (show: boolean) => void;
  setSelectedProvenance: (provenance: ProvenanceInfo | null) => void;
  setAvailableFolders: (folders: string[]) => void;
  
  // Animation control
  playAnimation: () => void;
  pauseAnimation: () => void;
  resetAnimation: () => void;
  nextStep: () => void;
  prevStep: () => void;
}

export const useStore = create<VeritasScopeState>((set, get) => ({
  // Initial state
  query: '',
  queryType: 'local',
  outputFolder: '',
  communityLevel: 2,
  temperature: 0.5,
  responseType: 'Multiple Paragraphs',
  isLoading: false,
  error: null,
  currentResponse: null,
  chatHistory: [],
  selectedNode: null,
  highlightedNodes: new Set(),
  currentStep: 0,
  isAnimating: false,
  showLabels: true,
  show3D: false,
  selectedProvenance: null,
  availableFolders: [],
  
  // Actions
  setQuery: (query) => set({ query }),
  setQueryType: (queryType) => set({ queryType }),
  setOutputFolder: (outputFolder) => set({ outputFolder }),
  setCommunityLevel: (communityLevel) => set({ communityLevel }),
  setTemperature: (temperature) => set({ temperature }),
  setResponseType: (responseType) => set({ responseType }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setCurrentResponse: (currentResponse) => set({ currentResponse }),
  
  addChatMessage: (message) => set((state) => ({
    chatHistory: [...state.chatHistory, message]
  })),
  
  clearChat: () => set({ chatHistory: [], currentResponse: null }),
  
  setSelectedNode: (selectedNode) => set({ selectedNode }),
  
  setHighlightedNodes: (highlightedNodes) => set({ highlightedNodes }),
  
  setCurrentStep: (currentStep) => set({ currentStep }),
  
  setIsAnimating: (isAnimating) => set({ isAnimating }),
  
  setShowLabels: (showLabels) => set({ showLabels }),
  
  setShow3D: (show3D) => set({ show3D }),
  
  setSelectedProvenance: (selectedProvenance) => set({ selectedProvenance }),
  
  setAvailableFolders: (availableFolders) => {
    set({ availableFolders });
    if (availableFolders.length > 0 && !get().outputFolder) {
      set({ outputFolder: availableFolders[0] });
    }
  },
  
  // Animation control
  playAnimation: () => {
    const { currentResponse, isAnimating } = get();
    if (isAnimating || !currentResponse?.reasoning_graph) return;
    
    set({ isAnimating: true });
    const steps = currentResponse.reasoning_graph.reasoning_steps;
    let stepIndex = get().currentStep;
    
    const interval = setInterval(() => {
      if (stepIndex >= steps.length - 1) {
        clearInterval(interval);
        set({ isAnimating: false });
        return;
      }
      stepIndex++;
      set({ currentStep: stepIndex });
      
      // Highlight nodes for current step
      const step = steps[stepIndex];
      set({ highlightedNodes: new Set(step.nodes_involved) });
    }, 1000);
  },
  
  pauseAnimation: () => set({ isAnimating: false }),
  
  resetAnimation: () => set({ currentStep: 0, highlightedNodes: new Set(), isAnimating: false }),
  
  nextStep: () => {
    const { currentResponse, currentStep } = get();
    if (!currentResponse?.reasoning_graph) return;
    
    const steps = currentResponse.reasoning_graph.reasoning_steps;
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      set({ 
        currentStep: nextStep,
        highlightedNodes: new Set(steps[nextStep].nodes_involved)
      });
    }
  },
  
  prevStep: () => {
    const { currentResponse, currentStep } = get();
    if (!currentResponse?.reasoning_graph) return;
    
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      const steps = currentResponse.reasoning_graph.reasoning_steps;
      set({ 
        currentStep: prevStep,
        highlightedNodes: new Set(steps[prevStep].nodes_involved)
      });
    }
  },
}));
