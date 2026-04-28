import Chart from "chart.js/auto";
import { useState, useRef, useEffect } from "react";
import VisitorCard from "./VisitorCard.jsx";

const API_BASE = "http://172.20.10.7:5000";

const mockRecordings = [
  { id: 1, timestamp: "2024-04-28 14:32", duration: "2s", faces: [{ id: "f1", name: "John", x: 10, y: 10, w: 20, h: 30 }], tagged: true, filename: "rec1.mp4" },
  { id: 2, timestamp: "2024-04-28 10:15", duration: "1s", faces: [{ id: "f2", name: "", x: 15, y: 15, w: 18, h: 28 }], tagged: false, filename: "rec2.mp4" },
];

const knownPeople = ["Sarah", "James", "Margaret", "Tom", "Delivery Person", "Neighbour"];

export default function DoorbellUI() {
  const [recordings, setRecordings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedFace, setSelectedFace] = useState(null);
  const [nameInput, setNameInput] = useState("");
  const [step, setStep] = useState("list");
  const [toast, setToast] = useState(null);
  const [videoError, setVideoError] = useState(null);
  const inputRef = useRef();
 
  
  // Fetch recordings from Pi API
  useEffect(() => {
    fetch("http://172.20.10.7:5000/api/recordings")
      .then(r => r.json())
      .then(data => setRecordings(data.map(r => ({
        id: r.id,
        timestamp: r.timestamp,
        duration: r.duration || "—",
        faces: r.faces || [],
        tagged: r.faces?.some(f => f.name),
        filename: r.filename,
      }))))
      .catch(e => {
        console.error("Failed to fetch recordings from Pi", e);
        setRecordings(mockRecordings);
      });
  }, []);

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

  const dashboardButton = (
    <button
      onClick={() => setStep("dashboard")}
      style={{
        marginBottom: 20,
        padding: "16px 22px",
        background: "#4F46E5",
        color: "white",
        border: "none",
        borderRadius: 14,
        fontSize: 20,
        fontWeight: 700,
        cursor: "pointer",
        boxShadow: "0 4px 14px rgba(79,70,229,0.3)",
      }}
    >
      View Dashboard
    </button>
  );

  // ── STEP 1: Recording List ──────────────────────────────────────────────
  if (step === "list") return (
    <Page>
      <TopBar title="🔔  My Doorbell" />

      {dashboardButton}

      <div style={{ margin: "20px 28px" }}>
        <VisitorCard />
      </div>

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

      {dashboardButton}

      <Section>
        <div style={{ fontSize: 20, color: "#444", marginBottom: 20, fontWeight: 600 }}>
          📅 {selected.timestamp} &nbsp;·&nbsp; {selected.duration}
        </div>

        {/* Video player */}
        <div style={{
          position: "relative", width: "100%", aspectRatio: "16/9",
          background: "#000",
          borderRadius: 20, overflow: "hidden",
          border: "3px solid #E5E7EB",
          marginBottom: 24,
          boxShadow: "0 6px 28px rgba(0,0,0,0.18)",
        }}>
          {videoError && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(0,0,0,0.8)", color: "#ff6b6b",
              flexDirection: "column", gap: 20, padding: 40, textAlign: "center", zIndex: 10,
            }}>
              <div style={{ fontSize: 18, fontWeight: 700 }}>❌ Video failed to load</div>
              <div style={{ fontSize: 14, color: "#ccc", wordBreak: "break-all" }}>
                URL: <br /> {`http://172.20.10.7:5000/api/video/${selected.filename}`}
              </div>
              <div style={{ fontSize: 13, color: "#aaa" }}>{videoError}</div>
            </div>
          )}
          <video
            key={selected.id}
            controls
            onError={(e) => {
              const msg = `${e.currentTarget.error?.message || e.currentTarget.error?.code || "Unknown error"}`;
              setVideoError(msg);
              console.error("Video error:", msg, "URL:", `http://172.20.10.7:5000/api/video/${selected.filename}`);
            }}
            onLoadStart={() => setVideoError(null)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: videoError ? "none" : "block",
            }}
          >
            <source
              src={`http://172.20.10.7:5000/api/video/${selected.filename}`}
              type="video/mp4"
            />
            Your browser does not support the video tag.
          </video>

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

      {dashboardButton}

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

  // Step 4 (Dashboard)
  if (step === "dashboard") return (
    <DashboardView setStep={setStep} />
  );
}

function DashboardView({ setStep }) {
  const [frequency, setFrequency] = useState([]);
  const [topVisitor, setTopVisitor] = useState(null);
  const [recent, setRecent] = useState([]);
  const [chart, setChart] = useState(null);
  const canvasRef = useRef();

  useEffect(() => {
    // Fetch visit frequency
    fetch(`${API_BASE}/api/visit-frequency`)
      .then(res => res.json())
      .then(setFrequency);

    // Fetch most frequent visitor
    fetch(`${API_BASE}/api/most-frequent-visitor`)
      .then(res => res.json())
      .then(setTopVisitor);

    // Fetch recent visitors
    fetch(`${API_BASE}/api/recent-visitors`)
      .then(res => res.json())
      .then(setRecent);

    // Fetch visits over time for line chart
    fetch(`${API_BASE}/api/visits-over-time`)
      .then(res => res.json())
      .then(data => {
        const labels = data.map(d => d.day);
        const values = data.map(d => d.visits);

        if (chart) chart.destroy();

        const newChart = new Chart(canvasRef.current, {
          type: "line",
          data: {
            labels,
            datasets: [
              {
                label: "Visits Over Time",
                data: values,
                borderColor: "#4F46E5",
                backgroundColor: "rgba(79,70,229,0.2)",
                borderWidth: 3,
                tension: 0.3
              }
            ]
          },
          options: {
            responsive: true,
            scales: {
              y: { beginAtZero: true }
            }
          }
        });

        setChart(newChart);
      });
  }, []);

  return (
    <Page>
      <TopBar
        title="Dashboard"
        onBack={() => setStep("list")}
        backLabel="← Back to recordings"
      />

      <Section title="Most Frequent Visitor">
        {topVisitor ? (
          <div style={{
            background: "#EEF2FF",
            padding: 20,
            borderRadius: 14,
            fontSize: 20,
            fontWeight: 700,
            color: "#3730A3"
          }}>
            {topVisitor.name || "Unknown"} — {topVisitor.visits} visits
          </div>
        ) : (
          <p>No data yet.</p>
        )}
      </Section>

      <Section title="Visits Over Time">
        <canvas ref={canvasRef} height="120"></canvas>
      </Section>

      <Section title="Visit Frequency">
        {frequency.map((item, i) => (
          <div key={i} style={{
            background: "white",
            padding: 16,
            borderRadius: 12,
            border: "2px solid #E5E7EB",
            marginBottom: 10,
            fontSize: 18
          }}>
            {item.name}: {item.visits} visits
          </div>
        ))}
      </Section>

      <Section title="Recent Visitors">
        {recent.map((item, i) => (
          <div key={i} style={{
            background: "#F9FAFB",
            padding: 16,
            borderRadius: 12,
            border: "2px solid #E5E7EB",
            marginBottom: 10
          }}>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {item.name || "Unknown"}
            </div>
            <div style={{ fontSize: 15, color: "#555" }}>
              Time: {item.time}
            </div>
            <div style={{ fontSize: 15, color: "#555" }}>
              Confidence: {item.confidence.toFixed(2)}
            </div>
          </div>
        ))}
      </Section>
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
