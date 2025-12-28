/**
 * API client for Veritas-Scope backend
 */

import axios from 'axios';
import type { QueryRequest, QueryResponse, FoldersResponse } from './types';

const API_BASE = '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for LLM queries
});

/**
 * Get list of available output folders
 */
export async function getFolders(): Promise<FoldersResponse> {
  const response = await apiClient.get<FoldersResponse>('/folders');
  return response.data;
}

/**
 * Execute a query with reasoning trace
 */
export async function executeQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await apiClient.post<QueryResponse>('/query', request);
  return response.data;
}

/**
 * Get full knowledge graph for a folder
 */
export async function getFullGraph(outputFolder: string, communityLevel: number = 2) {
  const response = await apiClient.get(`/graph/${outputFolder}`, {
    params: { community_level: communityLevel }
  });
  return response.data;
}

/**
 * Get details for a specific node
 */
export async function getNodeDetails(nodeId: string, outputFolder: string) {
  const response = await apiClient.post('/node/details', {
    node_id: nodeId,
    output_folder: outputFolder
  });
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await apiClient.get('/health');
  return response.data;
}

export default apiClient;
