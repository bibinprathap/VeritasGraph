/**
 * src/workspaces/LineageWorkspace/LineageDiagram.tsx
 */
import { useEffect, useState } from "react";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const THEME_CSS = `
  .react-flow { background: #0d1117; }
  .react-flow__node-group {
    background: rgba(88,166,255,0.05);
    border: 1px dashed rgba(88,166,255,0.2);
    border-radius: 8px;
  }
  .react-flow__node-default {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid rgba(88,166,255,0.3);
    border-radius: 6px;
    padding: 10px;
    white-space: pre-wrap;
    font-size: 12px;
  }
`;

export function LineageDiagram() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [searchId, setSearchId] = useState("");
  const [activeId, setActiveId] = useState("");

  const downloadReport = async (format: "json" | "markdown") => {
    if (!activeId) return;
    const response = await fetch(`/api/provenance/report?node_id=${encodeURIComponent(activeId)}&format=${format}`);
    if (!response.ok) {
      return;
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${activeId}_provenance.${format === "markdown" ? "md" : "json"}`;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(anchor);
  };

  useEffect(() => {
    if (!activeId) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const xLanes = [
      { id: "group_agent", type: "group", position: { x: 50, y: 50 }, style: { width: 800, height: 120 } },
      { id: "group_activity", type: "group", position: { x: 50, y: 200 }, style: { width: 800, height: 120 } },
      { id: "group_entity", type: "group", position: { x: 50, y: 350 }, style: { width: 800, height: 120 } }
    ];

    const fetchLineage = async () => {
      try {
        const res = await fetch("/api/provenance?node_id=" + encodeURIComponent(activeId));

        if (!res.ok) {
          const text = await res.text();
          console.error(`HTTP ${res.status}: API Route missing or failed.`, text.substring(0, 100));
          return;
        }

        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          console.error("Backend returned non-JSON response (likely an HTML fallback). Check FastAPI routing.");
          return;
        }

        const data = await res.json();

        const counters: Record<string, number> = { "group_agent": 0, "group_activity": 0, "group_entity": 0 };

        const mappedNodes = data.nodes.map((n: any) => {
          const c = counters[n.parent_id] || 0;
          counters[n.parent_id] = c + 1;
          return {
            id: n.id,
            data: { label: n.label + "\\n(" + n.prov_type + ")" },
            position: { x: 50 + c * 180, y: 30 },
            parentId: n.parent_id,
            extent: "parent",
            type: "default"
          };
        });

        const mappedEdges = data.edges.map((e: any) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          animated: true,
          style: { stroke: "#58a6ff" }
        }));

        setNodes([...xLanes, ...mappedNodes]);
        setEdges(mappedEdges);
      } catch (err) {
        console.error(err);
      }
    };
    fetchLineage();
  }, [activeId]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", background: "#0d1117" }}>
      <style>{THEME_CSS}</style>
      
      {/* Top Bar Navigation */}
      <div style={{ position: "absolute", top: 16, left: 16, zIndex: 10, display: "flex", gap: "12px", alignItems: "center" }}>
        <div style={{ background: "rgba(13,17,23,0.8)", padding: "4px 8px", borderRadius: 4, color: "#fff", fontWeight: 600, border: "1px solid rgba(255,255,255,0.1)", pointerEvents: "none" }}>
          PROV-O Lineage
        </div>
        
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            type="text"
            placeholder="Enter Node ID..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") setActiveId(searchId);
            }}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(88,166,255,0.3)",
              color: "#c9d1d9",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "12px",
              outline: "none",
              width: "200px"
            }}
          />
          <button
            onClick={() => setActiveId(searchId)}
            style={{
              background: "#1f6feb",
              color: "#fff",
              border: "none",
              padding: "5px 12px",
              borderRadius: "4px",
              fontSize: "12px",
              cursor: "pointer",
              fontWeight: 500
            }}
          >
            Search
          </button>
          <button
            onClick={() => void downloadReport("json")}
            disabled={!activeId}
            style={{
              background: "rgba(31, 111, 235, 0.18)",
              color: "#fff",
              border: "1px solid rgba(88,166,255,0.3)",
              padding: "5px 12px",
              borderRadius: "4px",
              fontSize: "12px",
              cursor: activeId ? "pointer" : "not-allowed",
              fontWeight: 500,
              opacity: activeId ? 1 : 0.5,
            }}
          >
            JSON
          </button>
          <button
            onClick={() => void downloadReport("markdown")}
            disabled={!activeId}
            style={{
              background: "rgba(31, 111, 235, 0.18)",
              color: "#fff",
              border: "1px solid rgba(88,166,255,0.3)",
              padding: "5px 12px",
              borderRadius: "4px",
              fontSize: "12px",
              cursor: activeId ? "pointer" : "not-allowed",
              fontWeight: 500,
              opacity: activeId ? 1 : 0.5,
            }}
          >
            Markdown
          </button>
        </div>
      </div>

      {activeId ? (
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="#30363d" gap={20} />
          <Controls />
        </ReactFlow>
      ) : (
        <div style={{ display: "flex", height: "100%", width: "100%", alignItems: "center", justifyContent: "center", color: "#8b949e", fontSize: "14px" }}>
          Enter a Node ID to view its W3C PROV-O lineage.
        </div>
      )}
    </div>
  );
}
