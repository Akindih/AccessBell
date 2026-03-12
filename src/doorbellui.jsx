import { useEffect, useRef, useState } from "react";

const API_BASE = "http://172.20.10.7:5000";
const knownPeople = ["Sarah", "James", "Margaret", "Tom", "Delivery Person", "Neighbour"];

function normalizeRecording(recording) {
  return {
    id: recording.id,
    timestamp: recording.timestamp,
    duration: recording.duration || "—",
    faces: Array.isArray(recording.faces) ? recording.faces : [],
    tagged: Array.isArray(recording.faces) ? recording.faces.every((face) => face.name) : false,
    filename: recording.filename,
    videoUrl: recording.video_url ? `${API_BASE}${recording.video_url}` : null,
  };
}

export default function DoorbellUI() {
  const [recordings, setRecordings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedFace, setSelectedFace] = useState(null);
  const [nameInput, setNameInput] = useState("");
  const [step, setStep] = useState("list");
  const [toast, setToast] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRecordings() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE}/api/recordings`);
        if (!response.ok) {
          throw new Error(`Unable to load recordings (${response.status})`);
        }
        const data = await response.json();
        if (!cancelled) {
          setRecordings(Array.isArray(data) ? data.map(normalizeRecording) : []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load recordings");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadRecordings();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const openRecording = (rec) => {
    setSelected(rec);
    setSelectedFace(null);
    setNameInput("");
    setStep("video");
  };

  const pickFace = (face) => {
    setSelectedFace(face);
    setNameInput(face.name || "");
    setStep("name");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const saveName = async (name) => {
    if (!name.trim() || !selected) return;

    const response = await fetch(`${API_BASE}/api/name-person`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_filename: selected.filename,
        name: name.trim(),
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to save name (${response.status})`);
    }

    const updated = recordings.map((rec) => {
      if (rec.id !== selected.id) return rec;
      const faces = rec.faces.map((face) =>
        face.id === selectedFace?.id ? { ...face, name: name.trim() } : face
      );
      return { ...rec, faces, tagged: true };
    });

    setRecordings(updated);
    setSelected(updated.find((rec) => rec.id === selected.id) || null);
    setToast(`✓ ${name} saved & added to dataset!`);
    setStep("video");
  };

  const untaggedCount = recordings.filter((rec) => rec.faces.some((face) => !face.name)).length;

  if (step === "list") {
    return (
      <Page>
        <TopBar title="🔔  My Doorbell" />
        {error && <Banner bg="#FEE2E2" border="#DC2626" text="#991B1B">Could not load recordings: {error}</Banner>}
        {loading && <Banner bg="#EEF2FF" border="#4F46E5" text="#3730A3">Loading recordings from Raspberry Pi...</Banner>}
        {untaggedCount > 0 && (
          <Banner bg="#FFF8E1" border="#F0AD00" text="#7A5500">
            ⚠️ &nbsp; You have <strong>{untaggedCount} visitor{untaggedCount > 1 ? "s" : ""}</strong> who haven't been named yet. Tap a video below to identify them.
          </Banner>
        )}
        <Section title="Recent Visitors">
          <p style={{ fontSize: 19, color: "#555", marginBottom: 24, lineHeight: 1.7 }}>
            Tap on a video to see who visited your door and give them a name.
          </p>
          {!loading && recordings.length === 0 && (
            <div style={{ background: "white", borderRadius: 18, padding: 24, border: "2px solid #E5E7EB", color: "#6B7280", fontSize: 18 }}>
              No recordings were returned by the Raspberry Pi server.
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {recordings.map((rec) => {
              const unknownCount = rec.faces.filter((face) => !face.name).length;
              const knownNames = rec.faces.filter((face) => face.name).map((face) => face.name);
              return (
                <button key={rec.id} onClick={() => openRecording(rec)} style={{ display: "flex", alignItems: "center", gap: 20, padding: "22px 24px", background: "white", border: `3px solid ${unknownCount > 0 ? "#F59E0B" : "#D1FAE5"}`, borderRadius: 20, cursor: "pointer", textAlign: "left", boxShadow: "0 3px 14px rgba(0,0,0,0.08)", width: "100%" }}>
                  <div style={{ width: 70, height: 70, borderRadius: 18, flexShrink: 0, background: unknownCount > 0 ? "#FEF3C7" : rec.faces.length === 0 ? "#F3F4F6" : "#D1FAE5", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36 }}>
                    {rec.faces.length === 0 ? "📹" : unknownCount > 0 ? "❓" : "✅"}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 21, fontWeight: 700, color: "#111", marginBottom: 5 }}>{rec.timestamp}</div>
                    <div style={{ fontSize: 17, color: "#666", marginBottom: 8 }}>Video length: {rec.duration}</div>
                    {rec.faces.length === 0 && <span style={pill("#E5E7EB", "#555")}>No face detected</span>}
                    {knownNames.map((name) => <span key={name} style={pill("#D1FAE5", "#065F46")}>✓ {name}</span>)}
                    {unknownCount > 0 && <span style={pill("#FEF3C7", "#92400E")}>⚠ {unknownCount} unknown — tap to name</span>}
                  </div>
                  <div style={{ fontSize: 34, color: "#CCC", flexShrink: 0 }}>›</div>
                </button>
              );
            })}
          </div>
        </Section>
        <Toast msg={toast} />
      </Page>
    );
  }

  if (step === "video" && selected) {
    return (
      <Page>
        <TopBar title="Who visited?" onBack={() => { setStep("list"); setSelected(null); }} backLabel="← Back to all videos" />
        <Section>
          <div style={{ fontSize: 20, color: "#444", marginBottom: 20, fontWeight: 600 }}>
            📅 {selected.timestamp} &nbsp;·&nbsp; {selected.duration}
          </div>
          <div style={{ position: "relative", width: "100%", aspectRatio: "16/9", background: "linear-gradient(160deg, #1c2a3a, #0e1825)", borderRadius: 20, overflow: "hidden", border: "3px solid #E5E7EB", marginBottom: 24, boxShadow: "0 6px 28px rgba(0,0,0,0.18)" }}>
            {selected.videoUrl ? (
              <video 
                key={selected.videoUrl} 
                controls 
                preload="metadata" 
                style={{ width: "100%", height: "100%", objectFit: "contain", background: "#000" }}
                onError={(e) => console.error("Video error:", e.target.error, "URL:", selected.videoUrl)}
              >
                <source src={selected.videoUrl} type="video/mp4" />
                Your browser does not support this video.
              </video>
            ) : (
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.35)", fontSize: 20, fontWeight: 600 }}>
                No video available for this clip
              </div>
            )}
          </div>
          {/* Debug info */}
          <div style={{ fontSize: 12, color: "#999", marginBottom: 16, wordBreak: "break-all" }}>
            Video URL: {selected.videoUrl || "none"} 
            {selected.videoUrl && <a href={selected.videoUrl} target="_blank" rel="noreferrer" style={{ marginLeft: 10, color: "#4F46E5" }}>[Open in new tab]</a>}
          </div>
          <div style={{ fontSize: 21, fontWeight: 800, color: "#111", marginBottom: 16 }}>People in this video:</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {selected.faces.map((face, i) => (
              <button key={face.id} onClick={() => pickFace(face)} style={{ display: "flex", alignItems: "center", gap: 18, padding: "18px 22px", background: face.name ? "#F0FDF4" : "#FFFBEB", border: `3px solid ${face.name ? "#BBF7D0" : "#FDE68A"}`, borderRadius: 16, cursor: "pointer", textAlign: "left", fontSize: 20, fontWeight: 700, color: face.name ? "#065F46" : "#92400E", width: "100%" }}>
                <span style={{ fontSize: 30 }}>{face.name ? "✅" : "❓"}</span>
                <span style={{ flex: 1 }}>{face.name || `Person ${i + 1}`}<span style={{ fontWeight: 500, fontSize: 16, color: "#777", marginLeft: 10 }}>{face.name ? "— identified ✓" : "— needs a name"}</span></span>
                <span style={{ fontSize: 28, color: "#CCC" }}>›</span>
              </button>
            ))}
          </div>
        </Section>
        <Toast msg={toast} />
      </Page>
    );
  }

  if (step === "name") {
    return (
      <Page>
        <TopBar title="Name this person" onBack={() => setStep("video")} backLabel="← Back to video" />
        <Section>
          <div style={{ width: 150, height: 150, borderRadius: "50%", background: "linear-gradient(135deg, #DBEAFE, #EDE9FE)", border: "4px solid #BFDBFE", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 70, margin: "0 auto 28px", boxShadow: "0 6px 24px rgba(99,102,241,0.15)" }}>👤</div>
          <p style={{ fontSize: 20, color: "#444", textAlign: "center", marginBottom: 36, lineHeight: 1.7 }}>Who is this person at your door?<br />Choose a name below, or type one yourself.</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 36 }}>
            {knownPeople.map((name) => (
              <button key={name} onClick={() => saveName(name)} style={{ padding: "20px 16px", background: "white", border: "3px solid #E5E7EB", borderRadius: 16, cursor: "pointer", fontSize: 20, fontWeight: 700, color: "#111", boxShadow: "0 2px 10px rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 12, textAlign: "left" }}>
                <span style={{ fontSize: 26 }}>👤</span> {name}
              </button>
            ))}
          </div>
          <input ref={inputRef} value={nameInput} onChange={(e) => setNameInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && saveName(nameInput)} placeholder="Type name here..." style={{ width: "100%", padding: "22px 24px", fontSize: 23, color: "#111", border: "3px solid #D1D5DB", borderRadius: 16, outline: "none", marginBottom: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.06)", fontFamily: "inherit" }} />
          <button onClick={() => saveName(nameInput)} disabled={!nameInput.trim()} style={{ width: "100%", padding: "24px", background: nameInput.trim() ? "#4F46E5" : "#E5E7EB", color: nameInput.trim() ? "white" : "#9CA3AF", border: "none", borderRadius: 18, fontSize: 23, fontWeight: 800, cursor: nameInput.trim() ? "pointer" : "not-allowed" }}>
            ✓ &nbsp; Save this name
          </button>
        </Section>
        <Toast msg={toast} />
      </Page>
    );
  }

  return null;
}

function Banner({ children, bg, border, text }) {
  return <div style={{ background: bg, borderLeft: `6px solid ${border}`, padding: "18px 28px", fontSize: 18, color: text, fontWeight: 700, lineHeight: 1.5 }}>{children}</div>;
}

function pill(bg, color) {
  return { display: "inline-block", background: bg, color, fontSize: 15, fontWeight: 700, padding: "5px 14px", borderRadius: 20, marginRight: 8, marginTop: 4 };
}

function Page({ children }) {
  return (
    <div style={{ minHeight: "100vh", background: "#F4F6F8", fontFamily: "'Nunito', 'Segoe UI', sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap'); * { box-sizing: border-box; margin: 0; padding: 0; } button, input { font-family: inherit; }`}</style>
      <div style={{ maxWidth: 800, margin: "0 auto", paddingBottom: 80 }}>{children}</div>
    </div>
  );
}

function TopBar({ title, onBack, backLabel }) {
  return (
    <div style={{ background: "white", borderBottom: "2px solid #E5E7EB", padding: "0 28px", position: "sticky", top: 0, zIndex: 50, boxShadow: "0 3px 14px rgba(0,0,0,0.07)" }}>
      {onBack && <button onClick={onBack} style={{ display: "block", paddingTop: 16, paddingBottom: 2, background: "none", border: "none", fontSize: 18, color: "#4F46E5", cursor: "pointer", fontWeight: 800 }}>{backLabel}</button>}
      <div style={{ padding: onBack ? "8px 0 20px" : "22px 0", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 52, height: 52, borderRadius: 16, flexShrink: 0, background: "linear-gradient(135deg, #4F46E5, #7C3AED)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, boxShadow: "0 4px 14px rgba(79,70,229,0.3)" }}>🔔</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "#111" }}>{title}</div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return <div style={{ padding: "30px 28px" }}>{title && <h2 style={{ fontSize: 26, fontWeight: 800, color: "#111", marginBottom: 22 }}>{title}</h2>}{children}</div>;
}

function Toast({ msg }) {
  if (!msg) return null;
  return <div style={{ position: "fixed", bottom: 36, left: "50%", transform: "translateX(-50%)", background: "#111", color: "white", padding: "20px 36px", borderRadius: 18, fontSize: 21, fontWeight: 700, boxShadow: "0 10px 40px rgba(0,0,0,0.25)", zIndex: 999, border: "3px solid #4ADE80", whiteSpace: "nowrap" }}>{msg}</div>;
}
