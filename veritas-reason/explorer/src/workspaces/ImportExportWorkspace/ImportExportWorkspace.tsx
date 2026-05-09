/**
 * src/workspaces/ImportExportWorkspace/ImportExportWorkspace.tsx
 */
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, Download, FileJson, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { logEvent } from "../../store/registryStore";

const THEME_CSS = `
  .glass-panel {
    background: linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.6));
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    border: 1px solid rgba(88,166,255,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 1px 1px 0 rgba(255,255,255,0.05);
  }
  .dropzone {
    border: 2px dashed rgba(88,166,255,0.4);
    border-radius: 12px;
    background: rgba(0,0,0,0.2);
    transition: all 0.2s ease-in-out;
    cursor: pointer;
  }
  .dropzone:hover, .dropzone.active {
    border-color: #58a6ff;
    background: rgba(88,166,255,0.05);
  }
  .btn-primary {
    background: #238636;
    color: #fff;
    border: 1px solid rgba(240,246,252,0.1);
    transition: background 0.2s;
  }
  .btn-primary:hover:not(:disabled) {
    background: #2ea043;
  }
  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .toast {
    animation: slideUp 0.3s ease-out forwards;
  }
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

interface ToastMessage {
  id: number;
  type: "success" | "error";
  text: string;
}

export function ImportExportWorkspace() {
  // Import State
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Export State
  const [exportFormat, setExportFormat] = useState<"json" | "csv">("json");
  const [isExporting, setIsExporting] = useState(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (type: "success" | "error", text: string) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, type, text }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
      'text/csv': ['.csv']
    },
    maxFiles: 1
  });

  const handleImport = async () => {
    if (!file) return;
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch("/api/import", {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Import failed");
      }
      
      const data = await res.json();
      showToast("success", `Imported ${data.nodes_imported} nodes and ${data.edges_imported} edges!`);
      logEvent("import", `Imported ${data.nodes_imported} nodes · ${data.edges_imported} edges from ${file.name}`, {
        file: file.name,
        nodesImported: data.nodes_imported,
        edgesImported: data.edges_imported,
      });
      setFile(null);
    } catch (err: any) {
      showToast("error", err.message || "An error occurred during import");
    } finally {
      setIsUploading(false);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: exportFormat })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Export failed");
      }
      
      // Handle file download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Provide a default extension based on format
      a.download = `veritasreason_export.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showToast("success", "Export complete! Your download should begin shortly.");
      logEvent("export", `Exported graph as ${exportFormat.toUpperCase()}`, { format: exportFormat });
    } catch (err: any) {
      showToast("error", err.message || "An error occurred during export");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div style={{ position: "relative", display: "flex", flexDirection: "column", width: "100%", height: "100%", background: "#0d1117", padding: 32, gap: 24, boxSizing: "border-box", overflowY: "auto" }}>
      <style>{THEME_CSS}</style>
      
      <div>
        <h1 style={{ margin: "0 0 8px 0", color: "#fff", display: "flex", alignItems: "center", gap: 12 }}>
          <UploadCloud size={28} color="#58a6ff" /> Data Import / Export
        </h1>
        <p style={{ margin: 0, color: "#8b949e" }}>Ingest new graph datasets or extract the current knowledge base.</p>
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        
        {/* IMPORT PANEL */}
        <div className="glass-panel" style={{ flex: "1 1 400px", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column" }}>
          <h2 style={{ margin: "0 0 24px 0", color: "#58a6ff", fontSize: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <UploadCloud size={20} /> Import Entities & Relations
          </h2>
          
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`} style={{ padding: 48, textAlign: "center", marginBottom: 24, flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <input {...getInputProps()} />
            {file ? (
              <>
                {file.name.endsWith(".json") ? <FileJson size={48} color="#3fb950" style={{ marginBottom: 16 }} /> : <FileText size={48} color="#3fb950" style={{ marginBottom: 16 }} />}
                <p style={{ color: "#fff", fontWeight: 600, margin: "0 0 8px 0" }}>{file.name}</p>
                <p style={{ color: "#8b949e", fontSize: 13, margin: 0 }}>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </>
            ) : (
              <>
                <UploadCloud size={48} color="#58a6ff" style={{ marginBottom: 16, opacity: 0.8 }} />
                <p style={{ color: "#c9d1d9", fontSize: 16, fontWeight: 500, margin: "0 0 8px 0" }}>Drag & drop your file here</p>
                <p style={{ color: "#8b949e", fontSize: 13, margin: 0 }}>Supports .json and .csv formats</p>
              </>
            )}
          </div>

          <button 
            className="btn-primary"
            onClick={handleImport}
            disabled={!file || isUploading}
            style={{ width: "100%", padding: "12px 24px", borderRadius: 8, fontSize: 16, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, cursor: (!file || isUploading) ? "not-allowed" : "pointer", border: "none" }}
          >
            {isUploading ? <Loader2 size={20} className="animate-spin" /> : <UploadCloud size={20} />}
            {isUploading ? "Uploading..." : "Upload to Graph"}
          </button>
        </div>

        {/* EXPORT PANEL */}
        <div className="glass-panel" style={{ flex: "1 1 400px", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column" }}>
          <h2 style={{ margin: "0 0 24px 0", color: "#d2a8ff", fontSize: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <Download size={20} /> Export Graph Snapshot
          </h2>
          
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", color: "#c9d1d9", marginBottom: 8, fontSize: 14, fontWeight: 500 }}>Export Format</label>
            <div style={{ position: "relative", marginBottom: 32 }}>
               <select 
                 value={exportFormat} 
                 onChange={e => setExportFormat(e.target.value as "json" | "csv")}
                 style={{ width: "100%", appearance: "none", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(88,166,255,0.3)", color: "#fff", padding: "12px 16px", borderRadius: 8, fontSize: 15, cursor: "pointer", outline: "none" }}
               >
                 <option value="json" style={{ background: "#0d1117" }}>JSON (Full Graph Dictionary)</option>
                 <option value="csv" style={{ background: "#0d1117" }}>CSV (Tabular Dump)</option>
               </select>
               <div style={{ position: "absolute", right: 16, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}>
                 <svg width="12" height="8" viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
                   <path d="M1.41 0.589966L6 5.16997L10.59 0.589966L12 1.99997L6 7.99997L0 1.99997L1.41 0.589966Z" fill="#8b949e"/>
                 </svg>
               </div>
            </div>

            <div style={{ background: "rgba(0,0,0,0.2)", padding: 20, borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)" }}>
              <h4 style={{ color: "#c9d1d9", margin: "0 0 8px 0", fontSize: 14 }}>Export Details</h4>
              <p style={{ color: "#8b949e", fontSize: 13, margin: 0, lineHeight: 1.5 }}>
                {exportFormat === "json" 
                  ? "Exports the entire graph including all node properties, edge weights, and complete entity metadata into a standardized JSON payload." 
                  : "Exports a flattened CSV tabular representation of all nodes and edges. Complex nested properties will be omitted or stringified."}
              </p>
            </div>
          </div>

          <button 
            style={{ width: "100%", background: "#1f6feb", color: "#fff", padding: "12px 24px", borderRadius: 8, fontSize: 16, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, cursor: isExporting ? "not-allowed" : "pointer", border: "1px solid rgba(240,246,252,0.1)", transition: "background 0.2s" }}
            onClick={handleExport}
            disabled={isExporting}
            onMouseOver={e => { if(!isExporting) (e.currentTarget.style.background = "#388bfd") }}
            onMouseOut={e => { if(!isExporting) (e.currentTarget.style.background = "#1f6feb") }}
          >
            {isExporting ? <Loader2 size={20} className="animate-spin" /> : <Download size={20} />}
            {isExporting ? "Preparing Extract..." : "Download Graph Extract"}
          </button>
        </div>
      </div>

      {/* Toast Notifications */}
      <div style={{ position: "fixed", bottom: 32, right: 32, display: "flex", flexDirection: "column", gap: 12, zIndex: 1000 }}>
        {toasts.map(toast => (
          <div key={toast.id} className="toast" style={{ 
            display: "flex", alignItems: "center", gap: 12, padding: "16px 20px", borderRadius: 8, 
            background: toast.type === 'success' ? '#1b4a24' : '#571822',
            border: `1px solid ${toast.type === 'success' ? 'rgba(63, 185, 80, 0.4)' : 'rgba(248, 81, 73, 0.4)'}`,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)"
          }}>
            {toast.type === 'success' ? <CheckCircle2 color="#3fb950" size={20}/> : <AlertCircle color="#f85149" size={20}/>}
            <span style={{ color: "#fff", fontSize: 14, fontWeight: 500 }}>{toast.text}</span>
          </div>
        ))}
      </div>

    </div>
  );
}