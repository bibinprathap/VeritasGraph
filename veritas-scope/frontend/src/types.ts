/**
 * Type definitions for Veritas-Scope
 */

export type NodeType = 'entity' | 'text_unit' | 'community' | 'document' | 'query' | 'answer';
export type NodeStatus = 'inactive' | 'entry_point' | 'traversed' | 'active' | 'final' | 'source';

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  status: NodeStatus;
  description?: string;
  rank?: number;
  community_id?: string;
  source_text?: string;
  document_id?: string;
  metadata?: Record<string, unknown>;
  size?: number;
  color?: string;
  x?: number;
  y?: number;
}

export interface GraphLink {
  id: string;
  source: string;
  target: string;
  relationship: string;
  weight?: number;
  hop_order?: number;
  is_reasoning_path: boolean;
  color?: string;
  width?: number;
  animated?: boolean;
}

export interface ReasoningStep {
  step_number: number;
  action: string;
  description: string;
  nodes_involved: string[];
  links_traversed: string[];
  timestamp?: string;
  confidence?: number;
  context_used?: string;
}

export interface ProvenanceInfo {
  source_id: string;
  source_type: string;
  source_title?: string;
  source_text: string;
  relevance_score?: number;
  page_number?: number;
  char_start?: number;
  char_end?: number;
  highlight_text?: string;
}

export interface ReasoningTraceGraph {
  nodes: GraphNode[];
  links: GraphLink[];
  reasoning_steps: ReasoningStep[];
  provenance: ProvenanceInfo[];
  total_nodes: number;
  total_links: number;
  total_hops: number;
  entry_nodes_count: number;
  final_nodes_count: number;
}

export interface QueryRequest {
  query: string;
  query_type: 'local' | 'global';
  output_folder?: string;
  community_level: number;
  temperature: number;
  response_type: string;
  include_graph: boolean;
  animate_trace: boolean;
}

export interface QueryResponse {
  query: string;
  answer: string;
  reasoning_graph?: ReasoningTraceGraph;
  completion_time: number;
  llm_calls: number;
  confidence_score?: number;
  query_type: string;
}

export interface FoldersResponse {
  folders: string[];
  default: string | null;
}

// Force graph types
export interface ForceGraphNode extends GraphNode {
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
}

export interface ForceGraphLink extends GraphLink {
  source: ForceGraphNode | string;
  target: ForceGraphNode | string;
}

export interface ForceGraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}
