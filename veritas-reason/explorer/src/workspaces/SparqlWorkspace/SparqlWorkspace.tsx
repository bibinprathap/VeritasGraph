/**
 * src/workspaces/SparqlWorkspace/SparqlWorkspace.tsx
 */
import { useState, useRef } from "react";
import Editor, { useMonaco } from "@monaco-editor/react";

const THEME_CSS = `
  .glass-panel {
    background: linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.6));
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    border: 1px solid rgba(88,166,255,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 1px 1px 0 rgba(255,255,255,0.05);
  }
`;

export function SparqlWorkspace() {
  const monaco = useMonaco();
  const editorRef = useRef<any>(null);
  const [query, setQuery] = useState("SELECT ?s ?p ?o\nWHERE {\n  ?s ?p ?o\n}\nLIMIT 10");
  const [result, setResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  function handleEditorWillMount(monacoIns: any) {
    if (!monacoIns.languages.getLanguages().some((l: any) => l.id === "sparql")) {
      monacoIns.languages.register({ id: "sparql" });

      monacoIns.languages.setMonarchTokensProvider("sparql", {
        keywords: ["SELECT", "WHERE", "LIMIT", "FILTER", "OPTIONAL", "PREFIX", "ORDER BY", "DESC", "ASC"],
        tokenizer: {
          root: [
            [/[a-zA-Z_]\w*/, { cases: { "@keywords": "keyword", "@default": "identifier" } }],
            [/[?\$][a-zA-Z_]\w*/, "variable.name"],
            [/<[^>]+>/, "string.uri"],
            [/".*?"/, "string"],
            [/#.*/, "comment"],
          ]
        }
      });

      monacoIns.editor.defineTheme("sparql-dark", {
        base: "vs-dark",
        inherit: true,
        rules: [
          { token: "keyword", foreground: "58a6ff", fontStyle: "bold" },
          { token: "variable.name", foreground: "79c0ff" },
          { token: "string.uri", foreground: "a5d6ff" },
          { token: "string", foreground: "a5d6ff" },
          { token: "comment", foreground: "8b949e" }
        ],
        colors: {
          "editor.background": "#0d1117",
          "editor.lineHighlightBackground": "#161b22",
        }
      });
    }
  }

  function handleEditorDidMount(editor: any) {
    editorRef.current = editor;
  }

  async function handleRun() {
    setIsLoading(true);
    setResult(null);
    monaco?.editor.setModelMarkers(editorRef.current.getModel(), "sparql", []);

    try {
      const response = await fetch("/api/sparql", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      const data = await response.json();

      if (data.error) {
        if (data.error_line && monaco && editorRef.current) {
          monaco.editor.setModelMarkers(editorRef.current.getModel(), "sparql", [
            {
              startLineNumber: data.error_line,
              startColumn: data.error_column || 1,
              endLineNumber: data.error_line,
              endColumn: 100,
              message: data.error,
              severity: monaco.MarkerSeverity.Error
            }
          ]);
        }
      }
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", background: "#0d1117", padding: 24, boxSizing: "border-box", gap: 24 }}>
      <style>{THEME_CSS}</style>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ color: "#ffffff", margin: 0, fontSize: 24 }}>SPARQL Query Engine</h2>
        <button
          onClick={handleRun}
          disabled={isLoading}
          style={{ background: "#238636", color: "#fff", border: "none", padding: "8px 24px", borderRadius: 6, fontWeight: 600, cursor: "pointer" }}
        >
          {isLoading ? "Running..." : "Run Query"}
        </button>
      </div>

      <div className="glass-panel" style={{ flex: 1, borderRadius: 12, overflow: "hidden", border: "1px solid rgba(88,166,255,0.2)" }}>
        <Editor
          height="100%"
          defaultLanguage="sparql"
          theme="sparql-dark"
          value={query}
          onChange={(v) => setQuery(v || "")}
          beforeMount={handleEditorWillMount}
          onMount={handleEditorDidMount}
          options={{ minimap: { enabled: false }, fontSize: 14, fontFamily: "monospace" }}
        />
      </div>

      <div className="glass-panel" style={{ height: "30%", borderRadius: 12, padding: 16, overflowY: "auto" }}>
        <h3 style={{ color: "#ffffff", margin: "0 0 16px 0", fontSize: 16 }}>Results</h3>
        {result?.error ? (
          <div style={{ color: "#ff7b72" }}>{result.error}</div>
        ) : result?.rows ? (
          <table style={{ width: "100%", borderCollapse: "collapse", color: "#c9d1d9" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                {result.columns.map((c: string) => <th key={c} style={{ textAlign: "left", padding: 8 }}>{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((r: any, i: number) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  {result.columns.map((c: string) => <td key={c} style={{ padding: 8 }}>{r[c]}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: "#8b949e" }}>No results to display. Run a query first.</div>
        )}
      </div>
    </div>
  );
}
