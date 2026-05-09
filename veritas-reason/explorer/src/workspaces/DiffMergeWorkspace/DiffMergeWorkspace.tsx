/**
 * src/workspaces/DiffMergeWorkspace/DiffMergeWorkspace.tsx
 */
import { useState } from "react";
import { logEvent } from "../../store/registryStore";

const THEME_CSS = `
  .glass-panel {
    background: linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.6));
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    border: 1px solid rgba(88,166,255,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 1px 1px 0 rgba(255,255,255,0.05);
  }
`;

export function DiffMergeWorkspace() {
  const [primaryId, setPrimaryId] = useState("n-primary-1");
  const [duplicateId, setDuplicateId] = useState("n-dup-2");

  const [msg, setMsg] = useState("");

  const handleMerge = async () => {
    try {
      const res = await fetch("/api/enrich/merge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ primary_id: primaryId, duplicate_ids: [duplicateId] })
      });
      const data = await res.json();
      if (data.merged_into) {
        setMsg(`Merge success: redirected ${data.edges_updated} edges to ${data.merged_into}`);
        logEvent("merge", `Merged ${duplicateId} → ${data.merged_into} · ${data.edges_updated} edges redirected`, {
          primary: data.merged_into,
          duplicate: duplicateId,
          edgesUpdated: data.edges_updated,
        });
      } else {
        setMsg("Merge failed...");
      }
    } catch (err) {
      setMsg("Error calling merge endpoint.");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", background: "#0d1117", padding: 32, gap: 24, boxSizing: "border-box" }}>
      <style>{THEME_CSS}</style>
      <div>
        <h1 style={{ margin: "0 0 8px 0", color: "#fff" }}>Entity Diff & Merge</h1>
        <p style={{ margin: 0, color: "#8b949e" }}>Compare suspected duplicate entities and reconcile them.</p>
      </div>

      <div style={{ display: "flex", gap: 24, flex: 1 }}>
        {/* Primary View */}
        <div className="glass-panel" style={{ flex: 1, borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: "#58a6ff", margin: "0 0 16px 0", borderBottom: "1px solid rgba(88,166,255,0.2)", paddingBottom: 8 }}>Primary Entity</h3>
          <label style={{ display: "block", color: "#c9d1d9", marginBottom: 8, fontSize: 13 }}>Primary Node ID</label>
          <input
            value={primaryId} onChange={e => setPrimaryId(e.target.value)}
            style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "8px 12px", borderRadius: 6, marginBottom: 24 }}
          />

          <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 6 }}>
            <div style={{ color: "#8b949e", fontSize: 12, marginBottom: 4 }}>Name</div>
            <div style={{ color: "#fff", fontSize: 14 }}>Sample Company Inc.</div>

            <div style={{ color: "#8b949e", fontSize: 12, marginTop: 16, marginBottom: 4 }}>Founded</div>
            <div style={{ color: "#fff", fontSize: 14 }}>2004-05-12</div>
          </div>
        </div>

        {/* Duplicate View */}
        <div className="glass-panel" style={{ flex: 1, borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: "#ff7b72", margin: "0 0 16px 0", borderBottom: "1px solid rgba(255,123,114,0.2)", paddingBottom: 8 }}>Duplicate Entity</h3>
          <label style={{ display: "block", color: "#c9d1d9", marginBottom: 8, fontSize: 13 }}>Duplicate Node ID</label>
          <input
            value={duplicateId} onChange={e => setDuplicateId(e.target.value)}
            style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "8px 12px", borderRadius: 6, marginBottom: 24 }}
          />

          <div style={{ background: "rgba(0,0,0,0.2)", padding: 16, borderRadius: 6 }}>
            <div style={{ color: "#d2a8ff", fontSize: 12, marginBottom: 4 }}>Name</div>
            {/* Amber highlight for differing values */}
            <div style={{ color: "#d29922", fontSize: 14, fontWeight: "bold" }}>Sample Company</div>

            <div style={{ color: "#8b949e", fontSize: 12, marginTop: 16, marginBottom: 4 }}>Founded</div>
            <div style={{ color: "#fff", fontSize: 14 }}>2004-05-12</div>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: "#58a6ff" }}>{msg}</div>
        <button
          onClick={handleMerge}
          style={{ background: "#238636", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 6, fontWeight: 600, cursor: "pointer", fontSize: 16 }}
        >
          Confirm Merge
        </button>
      </div>

    </div>
  );
}
