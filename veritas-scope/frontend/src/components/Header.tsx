/**
 * Header Component with branding and settings
 */

import { useState } from 'react';
import { useStore } from '../store';
import { 
  Settings, 
  Layers, 
  Thermometer, 
  FolderOpen,
  Search,
  Globe,
  MapPin,
  Eye,
  EyeOff,
  Box
} from 'lucide-react';

export default function Header() {
  const [showSettings, setShowSettings] = useState(false);
  
  const {
    queryType, setQueryType,
    outputFolder, setOutputFolder,
    communityLevel, setCommunityLevel,
    temperature, setTemperature,
    showLabels, setShowLabels,
    show3D, setShow3D,
    availableFolders,
    currentResponse
  } = useStore();
  
  return (
    <header className="bg-veritas-dark border-b border-white/10 px-6 py-3">
      <div className="flex items-center justify-between">
        {/* Logo and Title */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-veritas-primary to-veritas-secondary flex items-center justify-center">
              <Search className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">
                Veritas<span className="text-veritas-primary">Scope</span>
              </h1>
              <p className="text-xs text-white/50">Visual RAG Reasoning</p>
            </div>
          </div>
        </div>
        
        {/* Stats */}
        {currentResponse?.reasoning_graph && (
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-node-entity" />
              <span className="text-white/70">
                {currentResponse.reasoning_graph.total_nodes} nodes
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-node-query" />
              <span className="text-white/70">
                {currentResponse.reasoning_graph.total_hops} hops
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400" />
              <span className="text-white/70">
                {currentResponse.completion_time.toFixed(2)}s
              </span>
            </div>
          </div>
        )}
        
        {/* Quick Settings */}
        <div className="flex items-center gap-4">
          {/* Query Type Toggle */}
          <div className="flex items-center bg-white/5 rounded-lg p-1">
            <button
              onClick={() => setQueryType('local')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-all ${
                queryType === 'local' 
                  ? 'bg-veritas-primary text-white' 
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <MapPin className="w-4 h-4" />
              Local
            </button>
            <button
              onClick={() => setQueryType('global')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-all ${
                queryType === 'global' 
                  ? 'bg-veritas-primary text-white' 
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <Globe className="w-4 h-4" />
              Global
            </button>
          </div>
          
          {/* Output Folder */}
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-white/50" />
            <select
              value={outputFolder}
              onChange={(e) => setOutputFolder(e.target.value)}
              className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-veritas-primary"
            >
              {availableFolders.map(folder => (
                <option key={folder} value={folder} className="bg-veritas-dark">
                  {folder}
                </option>
              ))}
            </select>
          </div>
          
          {/* View Toggles */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowLabels(!showLabels)}
              className={`p-2 rounded transition-all ${
                showLabels ? 'bg-veritas-primary/20 text-veritas-primary' : 'text-white/50 hover:text-white'
              }`}
              title={showLabels ? 'Hide Labels' : 'Show Labels'}
            >
              {showLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setShow3D(!show3D)}
              className={`p-2 rounded transition-all ${
                show3D ? 'bg-veritas-primary/20 text-veritas-primary' : 'text-white/50 hover:text-white'
              }`}
              title={show3D ? '2D View' : '3D View'}
            >
              <Box className="w-4 h-4" />
            </button>
          </div>
          
          {/* Settings Button */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded transition-all ${
              showSettings ? 'bg-veritas-primary/20 text-veritas-primary' : 'text-white/50 hover:text-white'
            }`}
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Expanded Settings */}
      {showSettings && (
        <div className="mt-4 pt-4 border-t border-white/10 flex items-center gap-8">
          {/* Community Level */}
          <div className="flex items-center gap-3">
            <Layers className="w-4 h-4 text-white/50" />
            <span className="text-sm text-white/70">Community Level:</span>
            <input
              type="range"
              min={1}
              max={5}
              value={communityLevel}
              onChange={(e) => setCommunityLevel(parseInt(e.target.value))}
              className="w-24 accent-veritas-primary"
            />
            <span className="text-sm text-veritas-primary font-mono">{communityLevel}</span>
          </div>
          
          {/* Temperature */}
          <div className="flex items-center gap-3">
            <Thermometer className="w-4 h-4 text-white/50" />
            <span className="text-sm text-white/70">Temperature:</span>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-24 accent-veritas-primary"
            />
            <span className="text-sm text-veritas-primary font-mono">{temperature.toFixed(1)}</span>
          </div>
        </div>
      )}
    </header>
  );
}
