"use client";

import { useEffect, useRef, useState } from "react";
import "./globals.css";

const SAMPLES = [
  { label: "🗑️ Trash overflow (downtown)", text: "the trash is overflowing near the market", zone: "downtown", file: "garbage_overflow.jpg" },
  { label: "🚗 Illegal parking (downtown)", text: "a car is parked illegally blocking the road", zone: "downtown", file: "car_blocking.jpg" },
  { label: "🚙 Abandoned vehicle (suburb)", text: "a car has been abandoned here for weeks", zone: "far-suburb", file: "car_wreck.jpg" },
  { label: "❓ Out of scope", text: "please fix my electricity bill dispute", zone: "", file: "" },
];

function fakeFile(name) {
  // A tiny fake JPEG; the offline CV backend infers the object from the name.
  const blob = new Blob([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], { type: "image/jpeg" });
  return new File([blob], name, { type: "image/jpeg" });
}

export default function Home() {
  const [messages, setMessages] = useState([
    { role: "bot", text: "Hello! Describe a civic incident (trash overflow, abandoned vehicle, overcrowding, illegal parking) and attach a photo. I'll verify it and register a case." },
  ]);
  const [text, setText] = useState("");
  const [zone, setZone] = useState("downtown");
  const [locationText, setLocationText] = useState("");
  const [coords, setCoords] = useState(null); // {lat, lon}
  const [geoStatus, setGeoStatus] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cases, setCases] = useState([]);
  const [graph, setGraph] = useState(null);
  const chatRef = useRef(null);
  const fileInputRef = useRef(null);

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeoStatus("Geolocation not supported by this browser.");
      return;
    }
    setGeoStatus("Locating…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = +pos.coords.latitude.toFixed(6);
        const lon = +pos.coords.longitude.toFixed(6);
        setCoords({ lat, lon });
        setGeoStatus(`📍 ${lat}, ${lon}`);
      },
      (err) => setGeoStatus(`Could not get location: ${err.message}`),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function loadCases() {
    try {
      const r = await fetch("/api/cases");
      const j = await r.json();
      setCases(j.cases || []);
    } catch {}
  }
  async function loadGraph() {
    try {
      const r = await fetch("/api/graph");
      const j = await r.json();
      setGraph(j.stats || null);
    } catch {}
  }

  useEffect(() => {
    loadCases();
    loadGraph();
  }, []);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  async function send(overrideText, overrideZone, overrideFile) {
    const msgText = (overrideText ?? text).trim();
    if (!msgText || busy) return;
    const useZone = overrideZone ?? zone;
    const useFile = overrideFile !== undefined ? overrideFile : file;

    const locBits = [];
    if (useZone) locBits.push(useZone);
    if (locationText.trim()) locBits.push(locationText.trim());
    if (coords) locBits.push(`${coords.lat}, ${coords.lon}`);

    setMessages((m) => [
      ...m,
      {
        role: "user",
        text:
          msgText +
          (useFile ? `  📎 ${useFile.name}` : "") +
          (locBits.length ? `  📍 ${locBits.join(" / ")}` : "") +
          (name.trim() ? `  👤 ${name.trim()}` : ""),
      },
    ]);
    setText("");
    setBusy(true);

    try {
      const fd = new FormData();
      fd.append("text", msgText);
      if (useZone) fd.append("zone", useZone);
      if (locationText.trim()) fd.append("location_text", locationText.trim());
      if (coords) {
        fd.append("lat", String(coords.lat));
        fd.append("lon", String(coords.lon));
      }
      if (name.trim()) fd.append("name", name.trim());
      if (phone.trim()) fd.append("phone", phone.trim());
      if (email.trim()) fd.append("email", email.trim());
      if (useFile) fd.append("photo", useFile);
      const r = await fetch("/api/report", { method: "POST", body: fd });
      const j = await r.json();
      setMessages((m) => [...m, { role: "bot", text: j.message, result: j }]);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadCases();
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: "⚠️ Could not reach the server." }]);
    } finally {
      setBusy(false);
    }
  }

  function runSample(s) {
    setZone(s.zone);
    send(s.text, s.zone, s.file ? fakeFile(s.file) : null);
  }

  return (
    <div className="wrap">
      <div className="header">
        <h1>🏛️ Department of Municipality — Incident Reporting</h1>
        <p>
          Powered by <strong>VeritasGraph</strong> GraphRAG
          {graph ? ` · knowledge graph: ${graph.entities} nodes / ${graph.relationships} edges` : ""}
        </p>
      </div>

      <div className="layout">
        <div className="card">
          <div className="chat" ref={chatRef} data-testid="chat">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`} data-testid={`msg-${m.role}`}>
                {m.text}
                {m.result && m.result.outcome && (
                  <div>
                    <span className={`badge ${m.result.outcome}`} data-testid="outcome-badge">
                      {m.result.outcome}
                    </span>
                    {m.result.case_id && (
                      <div className="meta" data-testid="case-id">
                        Case {m.result.case_id} · {m.result.department} · SLA {m.result.sla_hours}h · score{" "}
                        {m.result.validation_score}
                      </div>
                    )}
                    {Array.isArray(m.result.reasoning_path) && m.result.reasoning_path.length > 0 && (
                      <div className="reason">↳ {m.result.reasoning_path.join("  ·  ")}</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="controls">
            <div className="row">
              <input
                type="text"
                placeholder="Describe the incident…"
                value={text}
                data-testid="message-input"
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
              />
            </div>

            <div className="row">
              <input
                type="text"
                placeholder="Address / landmark (e.g. 12 Market St)"
                value={locationText}
                data-testid="location-input"
                onChange={(e) => setLocationText(e.target.value)}
              />
              <button
                type="button"
                className="ghost"
                data-testid="geo-btn"
                onClick={useMyLocation}
              >
                📍 Use my location
              </button>
            </div>
            {geoStatus && (
              <div className="hint" data-testid="geo-status">{geoStatus}</div>
            )}

            <div className="row">
              <input
                type="text"
                placeholder="Your name"
                value={name}
                data-testid="name-input"
                onChange={(e) => setName(e.target.value)}
              />
              <input
                type="text"
                placeholder="Phone"
                value={phone}
                data-testid="phone-input"
                onChange={(e) => setPhone(e.target.value)}
              />
              <input
                type="email"
                placeholder="Email (optional)"
                value={email}
                data-testid="email-input"
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="row">
              <select value={zone} data-testid="zone-select" onChange={(e) => setZone(e.target.value)}>
                <option value="downtown">📍 downtown (has CCTV + sensors)</option>
                <option value="market">📍 market (has CCTV + sensors)</option>
                <option value="far-suburb">📍 far-suburb (no corroboration)</option>
                <option value="">📍 (no zone)</option>
              </select>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="file-label"
                data-testid="file-input"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <button data-testid="send-btn" disabled={busy} onClick={() => send()}>
                {busy ? "Verifying…" : "Send"}
              </button>
            </div>
          </div>

          <div className="hint">
            Offline demo: the CV backend infers the depicted object from the photo’s file name
            (e.g. <code>garbage_overflow.jpg</code>). Try a quick scenario →
          </div>
        </div>

        <div className="card side">
          <h2>Quick scenarios</h2>
          <div className="samples">
            {SAMPLES.map((s, i) => (
              <button key={i} data-testid={`sample-${i}`} disabled={busy} onClick={() => runSample(s)}>
                {s.label}
              </button>
            ))}
          </div>

          <div className="cases" style={{ marginTop: 20 }}>
            <h2>Registered cases ({cases.length})</h2>
            <div data-testid="cases-list">
              {cases.length === 0 && <div className="meta">No cases yet.</div>}
              {cases
                .slice()
                .reverse()
                .map((c) => (
                  <div key={c.id} className="case-item">
                    <span className="case-id">{c.id}</span> — {c.incident_code}
                    <div className="meta">
                      {c.department} · {c.status} · score {c.validation_score}
                    </div>
                    {c.reporter && (c.reporter.name || c.reporter.phone || c.reporter.email) && (
                      <div className="meta">
                        👤 {[c.reporter.name, c.reporter.phone, c.reporter.email].filter(Boolean).join(" · ")}
                      </div>
                    )}
                    {c.location && (c.location.text || c.location.zone || c.location.lat) && (
                      <div className="meta">
                        📍 {c.location.text || c.location.zone}
                        {c.location.lat != null ? ` (${c.location.lat}, ${c.location.lon})` : ""}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
