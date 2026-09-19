export type Confidence = "high" | "medium" | "low";

export type Provenance = {
  extractor?: string;
  page?: number;
  bbox?: number[];
  sourceText?: string;
};

export type GraphNode = {
  id: string;
  type: string;
  label: string;
  properties: Record<string, unknown>;
  provenance?: Provenance;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
};

export type GraphStats = {
  nodeCount: number;
  edgeCount: number;
  nodesByType: Record<string, number>;
  edgesByType: Record<string, number>;
};

export type Room = {
  id: string;
  name: string;
  page: number;
  bbox: number[];
  widthInches: number | null;
  heightInches: number | null;
  widthDisplay: string | null;
  heightDisplay: string | null;
  areaSqFt: number | null;
  perimeterFeet: number | null;
  sizeRaw: string | null;
  source: string;
  fixtures: string[];
};

export type ScheduleRow = Record<string, string | number | null>;

export type Schedule = {
  id: string;
  title: string;
  kind: string;
  page: number;
  columns: string[];
  rows: ScheduleRow[];
  rowCount: number;
  warnings: string[];
};

export type TakeoffLine = {
  id: string;
  csiSection: string;
  category: string;
  description: string;
  quantity: number;
  unit: string;
  basis: string;
  confidence: Confidence;
  sourceNodeIds: string[];
  sourcePages: number[];
  origin: "auto" | "manual" | "edited";
};

export type PageData = {
  page: number;
  width: number;
  height: number;
  textRunCount: number;
  rooms: Room[];
  areaCallouts: Array<{ label: string; areaSqFt: number; page: number; bbox: number[]; raw: string }>;
  dimensions: Array<{ raw: string; inches: number; feet: number; display: string; bbox: number[]; page: number }>;
  openings: Array<{ code: string; label: string; bbox: number[]; page: number; roomId?: string }>;
  fixtures: Array<{ code: string; label: string; category: string; bbox: number[]; page: number; roomId?: string }>;
  assemblies: Array<{ code: string; label: string; bbox: number[]; page: number }>;
};

export type ExtractionResult = {
  metadata: {
    engineVersion: string;
    processedAt: string;
    originalFilename: string;
    sha256: string;
    processingMethod: "pymupdf" | "pdfplumber";
    totalPages: number;
    durationMs: number;
  };
  summary: {
    totalPages: number;
    rooms: number;
    dimensions: number;
    openings: number;
    fixtures: number;
    schedules: number;
    scheduleRows: number;
    measuredAreaSqFt: number;
    takeoffLines: number;
  } & GraphStats;
  pages: PageData[];
  schedules: Schedule[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[]; stats: GraphStats };
  takeoff: {
    lines: TakeoffLine[];
    assumptions: Record<string, number>;
    totals: { lineCount: number; byUnit: Record<string, number>; byCategory: Record<string, number> };
  };
};
