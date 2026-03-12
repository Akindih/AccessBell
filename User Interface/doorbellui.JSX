import { useState, useRef } from "react";

const [recordings, setRecordings] = useState([]);

useEffect(() => {
  fetch("http://172.20.10.7:5000/api/recordings")
    .then(r => r.json())
    .then(data => setRecordings(data.map(r => ({
      id: r.id,
      timestamp: r.timestamp,
      duration: "—",
      faces: [],   // face detection can be added later
      tagged: false,
      filename: r.filename,
    }))));
}, []);

const knownPeople = ["Sarah", "James", "Margaret", "Tom", "Delivery Person", "Neighbour"];

export default function DoorbellUI() {
  const [recordings, setRecordings] = useState(mockRecordings);
  const [selected, setSelected] = useState(null);
  const [selectedFace, setSelectedFace] = useState(null);
  const [nameInput, setNameInput] = useState("");
  const [step, setStep] = useState("list");
  const [toast, setToast] = useState(null);
  const inputRef = useRef();

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

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
      if (!name.trim()) return;

      await fetch("http://172.20.10.7:5000/api/name-person", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_filename: selected.filename,
          name: name.trim(),
        }),
      });

      // Update UI state as before
      const updated = recordings.map(rec => {
        if (rec.id !== selected.id) return rec;
        const faces = rec.faces.map(f =>
          f.id === selectedFace?.id ? { ...f, name: name.trim() } : f
        );
        return { ...rec, faces, tagged: true };
      });
      setRecordings(updated);
      setSelected(updated.find(r => r.id === selected.id));
      showToast(`✓ ${name} saved & added to dataset!`);
      setStep("video");
};

  const untaggedCount = recordings.filter(r => r.faces.some(f => !f.name)).length;

  // ── STEP 1: Recording List ──────────────────────────────────────────────
  if (step === "list") return (
    <Page>
      <TopBar title="🔔  My Doorbell" />

      {untaggedCount > 0 && (
        <div style={{
          background: "#FFF8E1", borderLeft: "6px solid #F0AD00",
          padding: "18px 28px", fontSize: 20, color: "#7A5500",
          fontWeight: 600, lineHeight: 1.5,
        }}>
          ⚠️ &nbsp; You have <strong>{untaggedCount} visitor{untaggedCount > 1 ? "s" : ""}</strong> who haven't been named yet.
          Tap a video below to identify them.
        </div>
      )}

      <Section title="Recent Visitors">
        <p style={{ fontSize: 19, color: "#555", marginBottom: 24, lineHeight: 1.7 }}>
          Tap on a video to see who visited your door and give them a name.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {recordings.map(rec => {
            const unknownCount = rec.faces.filter(f => !f.name).length;
            const knownNames = rec.faces.filter(f => f.name).map(f => f.name);
            return (
              <button key={rec.id} onClick={() => openRecording(rec)} style={{
                display: "flex", alignItems: "center", gap: 20,
                padding: "22px 24px",
                background: "white",
                border: `3px solid ${unknownCount > 0 ? "#F59E0B" : "#D1FAE5"}`,
                borderRadius: 20,
                cursor: "pointer", textAlign: "left",
                boxShadow: "0 3px 14px rgba(0,0,0,0.08)",
                transition: "transform 0.15s, box-shadow 0.15s",
                width: "100%",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.13)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 3px 14px rgba(0,0,0,0.08)"; }}
              >
                <div style={{
                  width: 70, height: 70, borderRadius: 18, flexShrink: 0,
                  background: unknownCount > 0 ? "#FEF3C7" : rec.faces.length === 0 ? "#F3F4F6" : "#D1FAE5",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 36,
                }}>
                  {rec.faces.length === 0 ? "📹" : unknownCount > 0 ? "❓" : "✅"}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 21, fontWeight: 700, color: "#111", marginBottom: 5 }}>
                    {rec.timestamp}
                  </div>
                  <div style={{ fontSize: 17, color: "#666", marginBottom: 8 }}>
                    Video length: {rec.duration}
                  </div>
                  {rec.faces.length === 0 && (
                    <span style={pill("#E5E7EB", "#555")}>No face detected</span>
                  )}
                  {knownNames.map(n => (
                    <span key={n} style={pill("#D1FAE5", "#065F46")}>✓ {n}</span>
                  ))}
                  {unknownCount > 0 && (
                    <span style={pill("#FEF3C7", "#92400E")}>⚠ {unknownCount} unknown — tap to name</span>
                  )}
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

  // ── STEP 2: Video View ──────────────────────────────────────────────────
  if (step === "video") return (
    <Page>
      <TopBar title="Who visited?" onBack={() => { setStep("list"); setSelected(null); }} backLabel="← Back to all videos" />

      <Section>
        <div style={{ fontSize: 20, color: "#444", marginBottom: 20, fontWeight: 600 }}>
          📅 {selected.timestamp} &nbsp;·&nbsp; {selected.duration}
        </div>

        {/* Video mockup */}
        <div style={{
          position: "relative", width: "100%", aspectRatio: "16/9",
          background: "linear-gradient(160deg, #1c2a3a, #0e1825)",
          borderRadius: 20, overflow: "hidden",
          border: "3px solid #E5E7EB",
          marginBottom: 24,
          boxShadow: "0 6px 28px rgba(0,0,0,0.18)",
        }}>
          <div style={{
            position: "absolute", top: "15%", left: "38%", width: "24%", height: "78%",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: "6px 6px 0 0",
          }} />
          <div style={{
            position: "absolute", top: 14, left: 16, fontSize: 13,
            color: "rgba(255,255,255,0.5)", fontFamily: "monospace",
          }}>
            {selected.timestamp}
          </div>

          {selected.faces.length === 0 && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "rgba(255,255,255,0.35)", fontSize: 20, fontWeight: 600,
            }}>
              No faces were detected in this clip
            </div>
          )}

          {selected.faces.map((face, i) => (
            <button key={face.id} onClick={() => pickFace(face)} style={{
              position: "absolute",
              left: `${face.x}%`, top: `${face.y}%`,
              width: `${face.w}%`, height: `${face.h}%`,
              background: "rgba(255,255,255,0.05)",
              border: `4px solid ${face.name ? "#4ADE80" : "#FBBF24"}`,
              borderRadius: 10, cursor: "pointer",
              boxShadow: face.name ? "0 0 20px rgba(74,222,128,0.5)" : "0 0 20px rgba(251,191,36,0.5)",
              transition: "transform 0.15s",
            }}
              onMouseEnter={e => e.currentTarget.style.transform = "scale(1.04)"}
              onMouseLeave={e => e.currentTarget.style.transform = ""}
            >
              <div style={{
                position: "absolute", top: "15%", left: "20%", right: "20%", bottom: "5%",
                background: "rgba(255,255,255,0.07)", borderRadius: "50% 50% 40% 40%",
              }} />
              <div style={{
                position: "absolute", top: "calc(100% + 7px)", left: "50%",
                transform: "translateX(-50%)",
                background: face.name ? "#4ADE80" : "#FBBF24",
                color: face.name ? "#064E3B" : "#451A03",
                fontSize: 13, fontWeight: 800,
                padding: "4px 12px", borderRadius: 20, whiteSpace: "nowrap",
              }}>
                {face.name ? `✓ ${face.name}` : "TAP TO NAME"}
              </div>
            </button>
          ))}
        </div>

        {selected.faces.length > 0 && (
          <>
            <div style={{
              background: "#FFFBEB", border: "2px solid #FDE68A",
              borderRadius: 14, padding: "18px 22px", marginBottom: 28,
              fontSize: 19, color: "#78350F", lineHeight: 1.6,
            }}>
              👆 <strong>Tap on a face</strong> in the video above — or use the buttons below — to give that person a name.
            </div>

            <div style={{ fontSize: 21, fontWeight: 800, color: "#111", marginBottom: 16 }}>
              People in this video:
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {selected.faces.map((face, i) => (
                <button key={face.id} onClick={() => pickFace(face)} style={{
                  display: "flex", alignItems: "center", gap: 18,
                  padding: "18px 22px",
                  background: face.name ? "#F0FDF4" : "#FFFBEB",
                  border: `3px solid ${face.name ? "#BBF7D0" : "#FDE68A"}`,
                  borderRadius: 16, cursor: "pointer", textAlign: "left",
                  fontSize: 20, fontWeight: 700,
                  color: face.name ? "#065F46" : "#92400E",
                  width: "100%",
                  transition: "all 0.15s",
                }}
                  onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
                  onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                >
                  <span style={{ fontSize: 30 }}>{face.name ? "✅" : "❓"}</span>
                  <span style={{ flex: 1 }}>
                    {face.name ? `${face.name}` : `Person ${i + 1}`}
                    <span style={{ fontWeight: 500, fontSize: 16, color: "#777", marginLeft: 10 }}>
                      {face.name ? "— identified ✓" : "— needs a name"}
                    </span>
                  </span>
                  <span style={{ fontSize: 28, color: "#CCC" }}>›</span>
                </button>
              ))}
            </div>
          </>
        )}
      </Section>
      <Toast msg={toast} />
    </Page>
  );

  // ── STEP 3: Name This Person ────────────────────────────────────────────
  if (step === "name") return (
    <Page>
      <TopBar title="Name this person" onBack={() => setStep("video")} backLabel="← Back to video" />

      <Section>
        <div style={{
          width: 150, height: 150, borderRadius: "50%",
          background: "linear-gradient(135deg, #DBEAFE, #EDE9FE)",
          border: "4px solid #BFDBFE",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 70, margin: "0 auto 28px",
          boxShadow: "0 6px 24px rgba(99,102,241,0.15)",
        }}>👤</div>

        <p style={{ fontSize: 20, color: "#444", textAlign: "center", marginBottom: 36, lineHeight: 1.7 }}>
          Who is this person at your door?<br />
          Choose a name below, or type one yourself.
        </p>

        {selectedFace?.name && (
          <div style={{
            background: "#F0FDF4", border: "2px solid #BBF7D0",
            borderRadius: 14, padding: "16px 22px", marginBottom: 28,
            fontSize: 19, color: "#065F46",
            display: "flex", alignItems: "center", gap: 14,
          }}>
            <span style={{ fontSize: 28 }}>✅</span>
            <div>
              Currently saved as: <strong>{selectedFace.name}</strong><br />
              <span style={{ fontSize: 16, color: "#047857" }}>You can change this name below if needed.</span>
            </div>
          </div>
        )}

        <div style={{ fontSize: 21, fontWeight: 800, color: "#111", marginBottom: 16 }}>
          Choose a name:
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 36 }}>
          {knownPeople.map(name => (
            <button key={name} onClick={() => saveName(name)} style={{
              padding: "20px 16px",
              background: "white",
              border: "3px solid #E5E7EB",
              borderRadius: 16, cursor: "pointer",
              fontSize: 20, fontWeight: 700, color: "#111",
              boxShadow: "0 2px 10px rgba(0,0,0,0.06)",
              transition: "all 0.15s",
              display: "flex", alignItems: "center", gap: 12,
              textAlign: "left",
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "#4F46E5"; e.currentTarget.style.background = "#EEF2FF"; e.currentTarget.style.color = "#3730A3"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "#E5E7EB"; e.currentTarget.style.background = "white"; e.currentTarget.style.color = "#111"; }}
            >
              <span style={{ fontSize: 26 }}>👤</span> {name}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 28 }}>
          <div style={{ flex: 1, height: 2, background: "#E5E7EB" }} />
          <span style={{ fontSize: 18, color: "#9CA3AF", fontWeight: 700, whiteSpace: "nowrap" }}>Or type a new name</span>
          <div style={{ flex: 1, height: 2, background: "#E5E7EB" }} />
        </div>

        <input
          ref={inputRef}
          value={nameInput}
          onChange={e => setNameInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && saveName(nameInput)}
          placeholder="Type name here..."
          style={{
            width: "100%", padding: "22px 24px",
            fontSize: 23, color: "#111",
            border: "3px solid #D1D5DB", borderRadius: 16,
            outline: "none", marginBottom: 16,
            boxShadow: "0 2px 10px rgba(0,0,0,0.06)",
            fontFamily: "inherit",
          }}
          onFocus={e => e.target.style.borderColor = "#4F46E5"}
          onBlur={e => e.target.style.borderColor = "#D1D5DB"}
        />

        <button
          onClick={() => saveName(nameInput)}
          disabled={!nameInput.trim()}
          style={{
            width: "100%", padding: "24px",
            background: nameInput.trim() ? "#4F46E5" : "#E5E7EB",
            color: nameInput.trim() ? "white" : "#9CA3AF",
            border: "none", borderRadius: 18,
            fontSize: 23, fontWeight: 800,
            cursor: nameInput.trim() ? "pointer" : "not-allowed",
            transition: "all 0.2s",
            boxShadow: nameInput.trim() ? "0 6px 20px rgba(79,70,229,0.35)" : "none",
            letterSpacing: "0.01em",
          }}
        >
          ✓ &nbsp; Save this name
        </button>
      </Section>
      <Toast msg={toast} />
    </Page>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function pill(bg, color) {
  return {
    display: "inline-block",
    background: bg, color,
    fontSize: 15, fontWeight: 700,
    padding: "5px 14px", borderRadius: 20,
    marginRight: 8, marginTop: 4,
  };
}

function Page({ children }) {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#F4F6F8",
      fontFamily: "'Nunito', 'Segoe UI', sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        button, input { font-family: inherit; }
      `}</style>
      <div style={{ maxWidth: 800, margin: "0 auto", paddingBottom: 80 }}>
        {children}
      </div>
    </div>
  );
}

function TopBar({ title, onBack, backLabel }) {
  return (
    <div style={{
      background: "white",
      borderBottom: "2px solid #E5E7EB",
      padding: "0 28px",
      position: "sticky", top: 0, zIndex: 50,
      boxShadow: "0 3px 14px rgba(0,0,0,0.07)",
    }}>
      {onBack && (
        <button onClick={onBack} style={{
          display: "block", paddingTop: 16, paddingBottom: 2,
          background: "none", border: "none",
          fontSize: 18, color: "#4F46E5", cursor: "pointer",
          fontWeight: 800,
        }}>
          {backLabel}
        </button>
      )}
      <div style={{
        padding: onBack ? "8px 0 20px" : "22px 0",
        display: "flex", alignItems: "center", gap: 16,
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: 16, flexShrink: 0,
          background: "linear-gradient(135deg, #4F46E5, #7C3AED)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 26, boxShadow: "0 4px 14px rgba(79,70,229,0.3)",
        }}>🔔</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "#111" }}>{title}</div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ padding: "30px 28px" }}>
      {title && <h2 style={{ fontSize: 26, fontWeight: 800, color: "#111", marginBottom: 22 }}>{title}</h2>}
      {children}
    </div>
  );
}

function Toast({ msg }) {
  if (!msg) return null;
  return (
    <div style={{
      position: "fixed", bottom: 36, left: "50%",
      transform: "translateX(-50%)",
      background: "#111", color: "white",
      padding: "20px 36px", borderRadius: 18,
      fontSize: 21, fontWeight: 700,
      boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
      zIndex: 999, border: "3px solid #4ADE80",
      whiteSpace: "nowrap",
      animation: "fadeUp 0.3s ease",
    }}>
      <style>{`@keyframes fadeUp { from { opacity:0; transform:translateX(-50%) translateY(12px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }`}</style>
      {msg}
    </div>
  );
}
