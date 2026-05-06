import { useState, useRef, useEffect } from "react";
import VisitorCard from "./VisitorCard.jsx";

const API = "http://172.20.10.7:5000";
const knownPeople = ["Sarah", "James", "Margaret", "Tom", "Delivery Person", "Neighbour"];

// ── Relationship badge colours ───────────────────────────────────────────────
const REL_COLOURS = {
  family:   { bg: "#DBEAFE", color: "#1E40AF" },
  friend:   { bg: "#D1FAE5", color: "#065F46" },
  delivery: { bg: "#FEF3C7", color: "#92400E" },
  neighbour:{ bg: "#EDE9FE", color: "#5B21B6" },
  unknown:  { bg: "#F3F4F6", color: "#6B7280" },
};
function relStyle(rel = "") {
  const key = rel.toLowerCase();
  return REL_COLOURS[key] || REL_COLOURS.unknown;
}
function fmtDate(iso) {
  if (!iso) return "Never";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
function fmtConfidence(confidence) {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return "Confidence unavailable";
  return `${(confidence * 100).toFixed(1)}%`;
}

export default function DoorbellUI() {
  const [recordings, setRecordings] = useState([]);
  const [selected, setSelected]     = useState(null);
  const [selectedFace, setSelectedFace] = useState(null);
  const [nameInput, setNameInput]   = useState("");
  const [step, setStep]             = useState("list");
  const [toast, setToast]           = useState(null);
  const [videoError, setVideoError] = useState(null);
  const inputRef = useRef();

  useEffect(() => {
    fetch(`${API}/api/recordings`)
      .then(r => r.json())
      .then(data => setRecordings(data))
      .catch(e => { console.error("Failed to fetch recordings", e); setRecordings([]); });
  }, []);

  const showToast = msg => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const openRecording = rec => {
    setSelected(rec); setSelectedFace(null); setNameInput(""); setStep("video"); setVideoError(null);
  };

  const pickFace = face => {
    setSelectedFace(face); setNameInput(face.name || ""); setStep("name");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const saveName = async name => {
    if (!name.trim()) return;
    await fetch(`${API}/api/name-person`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_filename: selected.filename, name: name.trim() }),
    });
    showToast(`✓ ${name} saved!`);
    setStep("video");
  };

  // ── LIST ──────────────────────────────────────────────────────────────────
  if (step === "list") return (
    <Page>
      <TopBar title="🔔  My Doorbell" />
      <Section title="Recent Visitors">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {recordings.length === 0 && (
            <div style={{ textAlign: "center", color: "#9CA3AF", fontSize: 18, padding: 40 }}>
              No recordings yet.
            </div>
          )}
          {recordings.map(rec => {
            const hasKnown = rec.known_faces?.length > 0;
            return (
              <button key={rec.id} onClick={() => openRecording(rec)} style={{
                display: "flex", alignItems: "flex-start", gap: 18,
                padding: "20px 22px",
                background: "white",
                border: `3px solid ${rec.has_unknown ? "#E5E7EB" : "#BBF7D0"}`,
                borderRadius: 20, cursor: "pointer", textAlign: "left",
                boxShadow: "0 3px 14px rgba(0,0,0,0.07)", width: "100%",
                transition: "transform 0.15s, box-shadow 0.15s",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.13)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 3px 14px rgba(0,0,0,0.07)"; }}
              >
                {/* Icon */}
                <div style={{
                  width: 64, height: 64, borderRadius: 16, flexShrink: 0,
                  background: hasKnown ? "#D1FAE5" : "#F3F4F6",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32,
                }}>
                  {hasKnown ? "✅" : "📹"}
                </div>

                {/* Info */}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 19, fontWeight: 700, color: "#111", marginBottom: 6 }}>
                    {rec.timestamp}
                  </div>

                  {/* Recognised person pills */}
                  {hasKnown ? (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                      {rec.known_faces.map(f => {
                        const rs = relStyle(f.relationship);
                        return (
                          <div key={f.name} style={{
                            display: "flex", alignItems: "center", gap: 8,
                            background: rs.bg, color: rs.color,
                            border: `2px solid ${rs.color}22`,
                            borderRadius: 999, padding: "5px 14px", fontSize: 15, fontWeight: 700,
                          }}>
                            <span>👤</span>
                            <span>{f.name}</span>
                            <span style={{
                              background: rs.color, color: "white",
                              borderRadius: 999, padding: "1px 9px", fontSize: 12, fontWeight: 800,
                            }}>{f.relationship}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <span style={{ fontSize: 15, color: "#9CA3AF", fontWeight: 600 }}>
                      No one recognised
                    </span>
                  )}
                </div>

                <div style={{ fontSize: 30, color: "#CCC", flexShrink: 0, alignSelf: "center" }}>›</div>
              </button>
            );
          })}
        </div>
      </Section>
      <Toast msg={toast} />
    </Page>
  );

  // ── VIDEO VIEW ────────────────────────────────────────────────────────────
  if (step === "video") return (
    <Page>
      <TopBar title="Visitor Details" onBack={() => { setStep("list"); setSelected(null); }} backLabel="← Back" />
      <Section>
        {/* Timestamp */}
        <div style={{ fontSize: 18, color: "#6B7280", marginBottom: 18, fontWeight: 600 }}>
          📅 {selected.timestamp}
        </div>

        {/* Video player */}
        <div style={{
          position: "relative", width: "100%", aspectRatio: "16/9",
          background: "#000", borderRadius: 20, overflow: "hidden",
          border: "3px solid #E5E7EB", marginBottom: 28,
          boxShadow: "0 6px 28px rgba(0,0,0,0.18)",
        }}>
          {videoError && (
            <div style={{
              position: "absolute", inset: 0, display: "flex",
              alignItems: "center", justifyContent: "center",
              background: "rgba(0,0,0,0.85)", color: "#ff6b6b",
              flexDirection: "column", gap: 16, padding: 32, textAlign: "center", zIndex: 10,
            }}>
              <div style={{ fontSize: 42 }}>⚠️</div>
              <div style={{ fontSize: 17, fontWeight: 700 }}>Video could not be loaded</div>
              <div style={{ fontSize: 13, color: "#aaa" }}>{videoError}</div>
            </div>
          )}
          <video key={selected.id} controls
            onError={e => setVideoError(e.currentTarget.error?.message || "Unknown error")}
            onLoadStart={() => setVideoError(null)}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: videoError ? "none" : "block" }}
          >
            <source src={`${API}/api/video/${selected.filename}`} type="video/mp4" />
          </video>
        </div>

        <VisitorCard />

        {/* ── Person info cards ── */}
        {selected.known_faces?.length > 0 && (
          <>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#111", marginBottom: 16 }}>
              👥 People in this recording
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 28 }}>
              {selected.known_faces.map(face => {
                const rs = relStyle(face.relationship);
                const displayName = face.full_name || face.name;
                return (
                  <div key={face.name} style={{
                    background: "white", border: `3px solid ${rs.bg}`,
                    borderRadius: 18, padding: "20px 22px",
                    boxShadow: "0 3px 14px rgba(0,0,0,0.06)",
                  }}>
                    {/* Name + relationship */}
                    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
                      <div style={{
                        width: 52, height: 52, borderRadius: "50%",
                        background: rs.bg, display: "flex", alignItems: "center",
                        justifyContent: "center", fontSize: 26, flexShrink: 0,
                      }}>👤</div>
                      <div>
                        <div style={{ fontSize: 22, fontWeight: 800, color: "#111" }}>{displayName}</div>
                        <div style={{
                          display: "inline-block", marginTop: 4,
                          background: rs.bg, color: rs.color,
                          borderRadius: 999, padding: "3px 12px",
                          fontSize: 14, fontWeight: 800,
                        }}>{face.relationship}</div>
                      </div>
                    </div>

                    {/* Stats row */}
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <StatChip icon="🕐" label="Last seen" value={fmtDate(face.last_seen)} />
                      <StatChip icon="🔁" label="Total visits" value={face.visit_count} />
                      <StatChip icon="🎯" label="Confidence" value={fmtConfidence(face.confidence)} />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {selected.has_unknown && (
          <div style={{
            background: "#FFFBEB", border: "2px solid #FDE68A",
            borderRadius: 14, padding: "18px 22px", marginBottom: 28,
            fontSize: 18, color: "#78350F", lineHeight: 1.6,
          }}>
            ❓ <strong>No one was recognised</strong> in this recording.
            Use the Name Person feature to identify visitors.
          </div>
        )}

        {/* Name person button */}
        <button onClick={() => pickFace({ id: "manual", name: "" })} style={{
          width: "100%", padding: "20px",
          background: "#4F46E5", color: "white",
          border: "none", borderRadius: 16,
          fontSize: 20, fontWeight: 800, cursor: "pointer",
          boxShadow: "0 6px 20px rgba(79,70,229,0.3)",
        }}>
          ✏️ &nbsp; Name a person in this recording
        </button>
      </Section>
      <Toast msg={toast} />
    </Page>
  );

  // ── NAME PERSON ───────────────────────────────────────────────────────────
  if (step === "name") return (
    <Page>
      <TopBar title="Name this person" onBack={() => setStep("video")} backLabel="← Back to video" />
      <Section>
        <div style={{
          width: 120, height: 120, borderRadius: "50%",
          background: "linear-gradient(135deg,#DBEAFE,#EDE9FE)",
          border: "4px solid #BFDBFE",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 56, margin: "0 auto 28px",
        }}>👤</div>

        <p style={{ fontSize: 19, color: "#444", textAlign: "center", marginBottom: 32, lineHeight: 1.7 }}>
          Who is this person at your door?<br />Choose below or type a name.
        </p>

        <div style={{ fontSize: 20, fontWeight: 800, color: "#111", marginBottom: 14 }}>
          Quick select:
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 32 }}>
          {knownPeople.map(name => (
            <button key={name} onClick={() => saveName(name)} style={{
              padding: "18px 14px", background: "white",
              border: "3px solid #E5E7EB", borderRadius: 14,
              cursor: "pointer", fontSize: 18, fontWeight: 700, color: "#111",
              display: "flex", alignItems: "center", gap: 10, textAlign: "left",
              transition: "all 0.15s",
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "#4F46E5"; e.currentTarget.style.background = "#EEF2FF"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "#E5E7EB"; e.currentTarget.style.background = "white"; }}
            >
              <span>👤</span> {name}
            </button>
          ))}
        </div>

        <Divider label="Or type a name" />

        <input ref={inputRef} value={nameInput}
          onChange={e => setNameInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && saveName(nameInput)}
          placeholder="Type name here..."
          style={{
            width: "100%", padding: "20px 22px",
            fontSize: 21, color: "#111",
            border: "3px solid #D1D5DB", borderRadius: 14,
            outline: "none", marginBottom: 14, fontFamily: "inherit",
          }}
          onFocus={e => e.target.style.borderColor = "#4F46E5"}
          onBlur={e => e.target.style.borderColor = "#D1D5DB"}
        />
        <button onClick={() => saveName(nameInput)} disabled={!nameInput.trim()} style={{
          width: "100%", padding: "22px",
          background: nameInput.trim() ? "#4F46E5" : "#E5E7EB",
          color: nameInput.trim() ? "white" : "#9CA3AF",
          border: "none", borderRadius: 16,
          fontSize: 21, fontWeight: 800,
          cursor: nameInput.trim() ? "pointer" : "not-allowed",
          transition: "all 0.2s",
        }}>
          ✓ &nbsp; Save this name
        </button>
      </Section>
      <Toast msg={toast} />
    </Page>
  );
}

// ── Small components ─────────────────────────────────────────────────────────

function StatChip({ icon, label, value }) {
  return (
    <div style={{
      flex: 1, background: "#F9FAFB", borderRadius: 12,
      padding: "12px 14px", display: "flex", flexDirection: "column", gap: 4,
    }}>
      <div style={{ fontSize: 13, color: "#9CA3AF", fontWeight: 700 }}>{icon} {label}</div>
      <div style={{ fontSize: 17, fontWeight: 800, color: "#111" }}>{value}</div>
    </div>
  );
}

function Divider({ label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
      <div style={{ flex: 1, height: 2, background: "#E5E7EB" }} />
      <span style={{ fontSize: 16, color: "#9CA3AF", fontWeight: 700, whiteSpace: "nowrap" }}>{label}</span>
      <div style={{ flex: 1, height: 2, background: "#E5E7EB" }} />
    </div>
  );
}

function Page({ children }) {
  return (
    <div style={{ minHeight: "100vh", background: "#F4F6F8", fontFamily: "'Nunito','Segoe UI',sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap'); *{box-sizing:border-box;margin:0;padding:0;} button,input{font-family:inherit;}`}</style>
      <div style={{ maxWidth: 800, margin: "0 auto", paddingBottom: 80 }}>{children}</div>
    </div>
  );
}

function TopBar({ title, onBack, backLabel }) {
  return (
    <div style={{
      background: "white", borderBottom: "2px solid #E5E7EB",
      padding: "0 28px", position: "sticky", top: 0, zIndex: 50,
      boxShadow: "0 3px 14px rgba(0,0,0,0.07)",
    }}>
      {onBack && (
        <button onClick={onBack} style={{
          display: "block", paddingTop: 16, paddingBottom: 2,
          background: "none", border: "none",
          fontSize: 17, color: "#4F46E5", cursor: "pointer", fontWeight: 800,
        }}>{backLabel}</button>
      )}
      <div style={{ padding: onBack ? "8px 0 20px" : "22px 0", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{
          width: 48, height: 48, borderRadius: 14, flexShrink: 0,
          background: "linear-gradient(135deg,#4F46E5,#7C3AED)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 24, boxShadow: "0 4px 14px rgba(79,70,229,0.3)",
        }}>🔔</div>
        <div style={{ fontSize: 26, fontWeight: 800, color: "#111" }}>{title}</div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ padding: "28px 28px" }}>
      {title && <h2 style={{ fontSize: 24, fontWeight: 800, color: "#111", marginBottom: 20 }}>{title}</h2>}
      {children}
    </div>
  );
}

function Toast({ msg }) {
  if (!msg) return null;
  return (
    <div style={{
      position: "fixed", bottom: 36, left: "50%", transform: "translateX(-50%)",
      background: "#111", color: "white", padding: "18px 32px", borderRadius: 16,
      fontSize: 19, fontWeight: 700, boxShadow: "0 10px 40px rgba(0,0,0,0.25)",
      zIndex: 999, border: "3px solid #4ADE80", whiteSpace: "nowrap",
    }}>{msg}</div>
  );
}
