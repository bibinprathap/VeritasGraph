/**
 * Graph Panel - Interactive force-directed graph visualization
 */

import { useCallback, useMemo, useRef, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useStore } from '../store';
import type { GraphNode, ForceGraphNode, ForceGraphLink } from '../types';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';

// Node color mapping
const NODE_COLORS: Record<string, string> = {
  query: '#FF6B6B',
  entity: '#4ECDC4',
  text_unit: '#45B7D1',
  community: '#96CEB4',
  document: '#FFEAA7',
  answer: '#DDA0DD'
};

// Status-based opacity
const STATUS_OPACITY: Record<string, number> = {
  inactive: 0.3,
  entry_point: 1,
  traversed: 0.8,
  active: 1,
  final: 1,
  source: 0.7
};

export default function GraphPanel() {
  const graphRef = useRef<any>(null);
  
  const {
    currentResponse,
    selectedNode,
    setSelectedNode,
    highlightedNodes,
    showLabels,
    setSelectedProvenance
  } = useStore();
  
  // Transform data for force graph
  const graphData = useMemo(() => {
    if (!currentResponse?.reasoning_graph) {
      return { nodes: [], links: [] };
    }
    
    const { nodes, links } = currentResponse.reasoning_graph;
    
    // Transform nodes
    const transformedNodes: ForceGraphNode[] = nodes.map(node => ({
      ...node,
      x: node.x || Math.random() * 400 - 200,
      y: node.y || Math.random() * 400 - 200,
    }));
    
    // Transform links - ensure source/target are strings
    const transformedLinks: ForceGraphLink[] = links.map(link => ({
      ...link,
      source: typeof link.source === 'object' ? (link.source as any).id : link.source,
      target: typeof link.target === 'object' ? (link.target as any).id : link.target,
    }));
    
    return { nodes: transformedNodes, links: transformedLinks };
  }, [currentResponse]);
  
  // Node color function
  const getNodeColor = useCallback((node: ForceGraphNode) => {
    const baseColor = NODE_COLORS[node.type] || '#888888';
    const opacity = STATUS_OPACITY[node.status] || 0.5;
    
    // Highlight effect
    if (highlightedNodes.has(node.id)) {
      return baseColor;
    }
    
    // Selected node
    if (selectedNode?.id === node.id) {
      return baseColor;
    }
    
    // Apply opacity via alpha
    return `${baseColor}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
  }, [highlightedNodes, selectedNode]);
  
  // Node size function
  const getNodeSize = useCallback((node: ForceGraphNode) => {
    let size = node.size || 8;
    
    // Increase size for highlighted nodes
    if (highlightedNodes.has(node.id)) {
      size *= 1.5;
    }
    
    // Increase size for selected node
    if (selectedNode?.id === node.id) {
      size *= 1.8;
    }
    
    return size;
  }, [highlightedNodes, selectedNode]);
  
  // Link color function
  const getLinkColor = useCallback((link: ForceGraphLink) => {
    if (link.is_reasoning_path) {
      return link.animated ? '#FF6B6B' : '#FF6B6B88';
    }
    return '#ffffff22';
  }, []);
  
  // Link width function
  const getLinkWidth = useCallback((link: ForceGraphLink) => {
    if (link.is_reasoning_path) {
      return 2;
    }
    return 0.5;
  }, []);
  
  // Handle node click
  const handleNodeClick = useCallback((node: ForceGraphNode) => {
    setSelectedNode(node as GraphNode);
    
    // If it's a text unit, show provenance
    if (node.type === 'text_unit' && node.source_text) {
      setSelectedProvenance({
        source_id: node.id,
        source_type: 'text_unit',
        source_text: node.source_text,
        relevance_score: node.rank
      });
    }
  }, [setSelectedNode, setSelectedProvenance]);
  
  // Custom node canvas rendering
  const paintNode = useCallback((node: ForceGraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = getNodeSize(node);
    const color = getNodeColor(node);
    const isHighlighted = highlightedNodes.has(node.id) || selectedNode?.id === node.id;
    
    // Draw glow for highlighted nodes
    if (isHighlighted) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size * 1.5, 0, 2 * Math.PI);
      const gradient = ctx.createRadialGradient(
        node.x, node.y, size * 0.5,
        node.x, node.y, size * 2
      );
      gradient.addColorStop(0, `${NODE_COLORS[node.type]}66`);
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fill();
    }
    
    // Draw node
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    
    // Draw border
    ctx.strokeStyle = isHighlighted ? '#ffffff' : '#ffffff44';
    ctx.lineWidth = isHighlighted ? 2 : 0.5;
    ctx.stroke();
    
    // Draw label
    if (showLabels && globalScale > 0.5) {
      const label = node.label.length > 20 ? node.label.substring(0, 20) + '...' : node.label;
      const fontSize = Math.max(10 / globalScale, 3);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, node.x, node.y + size + 2);
    }
  }, [getNodeColor, getNodeSize, highlightedNodes, selectedNode, showLabels]);
  
  // Zoom controls
  const handleZoomIn = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom * 1.5, 400);
    }
  };
  
  const handleZoomOut = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom / 1.5, 400);
    }
  };
  
  const handleZoomFit = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 50);
    }
  };
  
  const handleReset = () => {
    if (graphRef.current) {
      graphRef.current.centerAt(0, 0, 400);
      graphRef.current.zoom(1, 400);
    }
  };
  
  // Auto-fit on new data
  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 50);
      }, 500);
    }
  }, [graphData]);
  
  if (!currentResponse?.reasoning_graph) {
    return (
      <div className="flex-1 flex items-center justify-center bg-veritas-darker">
        <div className="text-center">
          <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
            <svg 
              className="w-12 h-12 text-white/20"
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="1.5"
            >
              <circle cx="12" cy="12" r="3" />
              <circle cx="4" cy="8" r="2" />
              <circle cx="20" cy="8" r="2" />
              <circle cx="4" cy="16" r="2" />
              <circle cx="20" cy="16" r="2" />
              <line x1="9" y1="11" x2="6" y2="9" />
              <line x1="15" y1="11" x2="18" y2="9" />
              <line x1="9" y1="13" x2="6" y2="15" />
              <line x1="15" y1="13" x2="18" y2="15" />
            </svg>
          </div>
          <p className="text-white/40 text-sm">
            Ask a question to see the reasoning graph
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex-1 relative bg-veritas-darker">
      {/* Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, getNodeSize(node as ForceGraphNode) * 1.5, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkColor={getLinkColor}
        linkWidth={getLinkWidth}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.15}
        onNodeClick={handleNodeClick}
        backgroundColor="#16162a"
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
      
      {/* Zoom Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-all"
          title="Zoom In"
        >
          <ZoomIn className="w-5 h-5" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-all"
          title="Zoom Out"
        >
          <ZoomOut className="w-5 h-5" />
        </button>
        <button
          onClick={handleZoomFit}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-all"
          title="Fit to View"
        >
          <Maximize2 className="w-5 h-5" />
        </button>
        <button
          onClick={handleReset}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-all"
          title="Reset View"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
      </div>
      
      {/* Legend */}
      <div className="absolute top-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg p-3">
        <p className="text-xs text-white/50 mb-2 font-medium">NODE TYPES</p>
        <div className="space-y-1.5">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-white/70 capitalize">
                {type.replace('_', ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Selected Node Info */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-64 bg-black/50 backdrop-blur-sm rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: NODE_COLORS[selectedNode.type] }}
            />
            <span className="text-sm font-medium text-white truncate">
              {selectedNode.label}
            </span>
          </div>
          <p className="text-xs text-white/50 capitalize mb-2">
            {selectedNode.type.replace('_', ' ')} • {selectedNode.status.replace('_', ' ')}
          </p>
          {selectedNode.description && (
            <p className="text-xs text-white/70 line-clamp-4">
              {selectedNode.description}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
