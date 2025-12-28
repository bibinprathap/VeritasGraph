/**
 * Main App Component for Veritas-Scope
 */

import { useEffect } from 'react';
import { useStore } from './store';
import { getFolders } from './api';
import Header from './components/Header';
import ChatPanel from './components/ChatPanel';
import GraphPanel from './components/GraphPanel';
import ProvenancePanel from './components/ProvenancePanel';
import ReasoningSteps from './components/ReasoningSteps';

export default function App() {
  const { setAvailableFolders, setError } = useStore();
  
  useEffect(() => {
    // Load available folders on mount
    const loadFolders = async () => {
      try {
        const data = await getFolders();
        setAvailableFolders(data.folders);
      } catch (err) {
        console.error('Failed to load folders:', err);
        setError('Failed to connect to Veritas-Scope API. Make sure the backend is running.');
      }
    };
    
    loadFolders();
  }, [setAvailableFolders, setError]);
  
  return (
    <div className="h-screen flex flex-col bg-veritas-darker overflow-hidden">
      {/* Header */}
      <Header />
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Chat Interface */}
        <div className="w-[400px] flex-shrink-0 border-r border-white/10 flex flex-col">
          <ChatPanel />
        </div>
        
        {/* Center: Graph Visualization */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <GraphPanel />
          
          {/* Reasoning Steps Timeline */}
          <ReasoningSteps />
        </div>
        
        {/* Right Panel: Provenance/Source Viewer */}
        <ProvenancePanel />
      </div>
    </div>
  );
}
