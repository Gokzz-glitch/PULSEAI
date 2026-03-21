/// <reference types="vite/client" />
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

interface DiagnosticReport {
  status?: string;
  conclusion?: string;
  id?: string;
  extension?: Array<{ url: string; valueString?: string; valueDecimal?: number }>;
}

interface PredictionPayload {
  type: string;
  classification?: string;
  confidence?: number;
  heart_rate_bpm?: number;
  rr_cv?: number;
  signal_quality?: string;
  model_used?: string;
  explainability_map?: Record<string, unknown> | null;
  ecg_snapshot?: number[];
  fhir_report?: DiagnosticReport;
}

const BACKEND = import.meta.env.VITE_BACKEND_URL || `${window.location.protocol}//${window.location.hostname}:8000`;
const WS_URL = `${BACKEND.replace(/^http/, 'ws')}/ws`;

// ─── Icons ──────────────────────────────────────────────────
const ActivityIcon = ({ size = 28, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);
const ShieldIcon = ({ size = 14, color = 'var(--violet)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);
const CpuIcon = ({ size = 14, color = 'var(--cyan)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="6" height="6" /><rect x="2" y="2" width="20" height="20" rx="2" />
    <line x1="9" y1="2" x2="9" y2="6" /><line x1="15" y1="2" x2="15" y2="6" />
    <line x1="9" y1="18" x2="9" y2="22" /><line x1="15" y1="18" x2="15" y2="22" />
    <line x1="2" y1="9" x2="6" y2="9" /><line x1="2" y1="15" x2="6" y2="15" />
    <line x1="18" y1="9" x2="22" y2="9" /><line x1="18" y1="15" x2="22" y2="15" />
  </svg>
);
const AlertIcon = ({ size = 32, color = 'var(--rose)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);
const CheckIcon = ({ size = 32, color = 'var(--cyan)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);
const UserIcon = ({ size = 20, color = 'var(--cyan)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
);
const WifiIcon = ({ size = 14, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/>
    <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>
  </svg>
);

// ─── Particle Background ─────────────────────────────────────
const ParticleBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let W = window.innerWidth, H = window.innerHeight;
    canvas.width = W; canvas.height = H;

    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
      a: Math.random(),
      color: Math.random() > 0.5 ? '0,245,212' : '167,139,250',
    }));

    let raf: number;
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color},${p.a * 0.6})`;
        ctx.fill();
      });
      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0,245,212,${0.06 * (1 - dist / 100)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();

    const resize = () => {
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = W; canvas.height = H;
    };
    window.addEventListener('resize', resize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);

  return <canvas ref={canvasRef} id="particle-canvas" />;
};

// ─── Robot AI Scanner ────────────────────────────────────────
const RobotAI = ({ isAnomaly }: { isAnomaly: boolean }) => (
  <div className={`robot-scanner ${isAnomaly ? 'robot-alert' : 'robot-thinking'}`}>
    <div className="robot-head">
      <div className="robot-eye left" />
      <div className="robot-eye right" />
    </div>
    <div className="robot-ring" />
    <div className="laser-beam" />
    <div className="robot-status-text">
      {isAnomaly ? '⚡ ANOMALY DETECTED' : '● ANALYZING SIGNAL'}
    </div>
  </div>
);

// ─── Heartbeat ───────────────────────────────────────────────
const HeartPulse = ({ bpm = 70, status = 'normal' }) => {
  const duration = 60 / Math.max(bpm, 30);
  const color = status === 'normal' ? 'var(--cyan)' : 'var(--rose)';
  return (
    <div className="heart-dt" style={{ '--heart-speed': `${duration}s` } as React.CSSProperties}>
      <svg width="36" height="36" viewBox="0 0 24 24" fill={color} className="heart-svg">
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
      </svg>
      <div className="heart-aura" style={{ background: color }} />
    </div>
  );
};

// ─── JSON Syntax Highlighter ─────────────────────────────────
const syntaxHighlight = (json: string) => {
  return json
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
      let cls = 'fhir-number';
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'fhir-key' : 'fhir-string';
      } else if (/true|false/.test(match)) {
        cls = 'fhir-bool';
      } else if (/null/.test(match)) {
        cls = 'fhir-null';
      }
      return `<span class="${cls}">${match}</span>`;
    });
};

// ─── App ─────────────────────────────────────────────────────
function App() {
  const [consentGiven, setConsentGiven] = useState(false);
  const [ecgData, setEcgData] = useState<number[]>([]);
  const [diagnostic, setDiagnostic] = useState<DiagnosticReport>({ status: 'Awaiting ECG stream...' });
  const [leadsOff, setLeadsOff] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const [lastPrediction, setLastPrediction] = useState<PredictionPayload | null>(null);
  const [tick, setTick] = useState(0);
  const mockRef   = useRef<number | null>(null);
  const wsRef     = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const pingRef   = useRef<number | null>(null);
  const fhirRef   = useRef<HTMLPreElement>(null);

  // ── Clock tick for live timestamp ─────────────────────────
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // ── Fallback REST polling ──────────────────────────────────
  useEffect(() => {
    if (!consentGiven) return;
    const poll = setInterval(async () => {
      try {
        const [ecgRes, diagRes] = await Promise.all([
          fetch(`${BACKEND}/api/ecg`),
          fetch(`${BACKEND}/api/diagnostic`),
        ]);
        const ecgJson = await ecgRes.json();
        const diagJson = await diagRes.json();
        if (ecgJson.data?.length) setEcgData(ecgJson.data);
        if (ecgJson.leads_off !== undefined) setLeadsOff(ecgJson.leads_off);
        if (diagJson) setDiagnostic(diagJson);
        if (connectionState !== 'live') setConnectionState('connecting');
      } catch (_) {}
    }, 2000);
    return () => clearInterval(poll);
  }, [consentGiven, connectionState]);

  // ── WebSocket ──────────────────────────────────────────────
  useEffect(() => {
    if (!consentGiven) return;
    let closedManually = false;

    const connect = () => {
      setConnectionState('connecting');
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState('live');
        if (pingRef.current) clearInterval(pingRef.current);
        pingRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as PredictionPayload;
          if (payload.type === 'leads_off') { setLeadsOff(true); return; }
          if (payload.type === 'snapshot') {
            if (Array.isArray(payload.ecg_snapshot) && payload.ecg_snapshot.length)
              setEcgData(payload.ecg_snapshot);
            return;
          }
          if (payload.type === 'prediction') {
            if (Array.isArray(payload.ecg_snapshot) && payload.ecg_snapshot.length)
              setEcgData(payload.ecg_snapshot);
            setLeadsOff(false);
            setLastPrediction(payload);
            if (payload.fhir_report) setDiagnostic(payload.fhir_report);
            else if (payload.classification) setDiagnostic({ status: 'monitoring', conclusion: payload.classification });
          }
        } catch (_) {}
      };

      ws.onerror = () => setConnectionState('offline');
      ws.onclose = () => {
        if (pingRef.current) clearInterval(pingRef.current);
        if (closedManually) return;
        setConnectionState('offline');
        reconnectRef.current = window.setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closedManually = true;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (pingRef.current) clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [consentGiven]);

  // ── Mock ECG when offline ──────────────────────────────────
  useEffect(() => {
    if (!consentGiven || connectionState === 'live') {
      if (mockRef.current) clearInterval(mockRef.current);
      return;
    }
    mockRef.current = window.setInterval(() => {
      setEcgData((prev: number[]) => {
        const t = Date.now() / 200;
        const val = Math.sin(t) * 30 + Math.sin(t * 4.2) * 10 + (Math.random() - 0.5) * 5 + 50;
        const next = [...prev, val];
        return next.length > 120 ? next.slice(next.length - 120) : next;
      });
    }, 80);
    return () => { if (mockRef.current) clearInterval(mockRef.current); };
  }, [consentGiven, connectionState]);

  // ── Syntax-highlight FHIR JSON ─────────────────────────────
  useEffect(() => {
    if (fhirRef.current) {
      fhirRef.current.innerHTML = syntaxHighlight(JSON.stringify(diagnostic, null, 2));
    }
  }, [diagnostic]);

  // ── Derived state ──────────────────────────────────────────
  const modelLabel    = lastPrediction?.model_used || 'HCTG-Net Local';
  const confidence    = lastPrediction?.confidence;
  const heartRate     = lastPrediction?.heart_rate_bpm;
  const rrCV          = lastPrediction?.rr_cv;
  const signalQuality = lastPrediction?.signal_quality || 'good';
  const isAnomaly     = !!(diagnostic?.conclusion && !diagnostic.conclusion.toLowerCase().includes('normal sinus'));

  const gradCamExt = diagnostic?.extension?.find(e => e.url.includes('gradcam'));
  let gradCamMap: Record<string, unknown> | null = null;
  if (gradCamExt?.valueString) {
    try { gradCamMap = JSON.parse(gradCamExt.valueString); } catch (_) {}
  }

  const signalQualityColor = signalQuality === 'poor' ? 'var(--rose)' : signalQuality === 'fair' ? 'var(--amber)' : 'var(--cyan)';
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const chartData = useMemo(() => ({
    labels: ecgData.map((_: number, i: number) => i.toString()),
    datasets: [{
      data: ecgData,
      borderColor: isAnomaly ? '#f43f5e' : '#00f5d4',
      backgroundColor: isAnomaly ? 'rgba(244,63,94,0.05)' : 'rgba(0,245,212,0.04)',
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 0,
      fill: true,
    }],
  }), [ecgData, isAnomaly]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false as const,
    scales: {
      x: { display: false },
      y: {
        min: -10, max: 120,
        grid: { color: 'rgba(255,255,255,0.025)' },
        ticks: { color: '#4a5280', font: { size: 9 }, maxTicksLimit: 5 },
        border: { display: false },
      },
    },
    plugins: { legend: { display: false } },
  };

  // ═══════════════════════════════════════════
  // CONSENT SCREEN
  // ═══════════════════════════════════════════
  if (!consentGiven) {
    return (
      <div className="app-shell">
        <ParticleBackground />
        <div className="consent-wrap">
          <div className="consent-card anim">
            <div className="consent-logo">
              <div className="consent-logo-bg">
                <ActivityIcon size={32} color="var(--cyan)" />
              </div>
              <div className="consent-logo-ring" />
            </div>
            <h1 className="consent-title">PulseAI Nexus</h1>
            <p className="consent-sub">AI-Driven Cardiac Arrhythmia Triage Platform · Real-Time ECG Analysis</p>

            <div className="consent-notice">
              <div className="consent-notice-title">🚨 DPDP Act 2023 — Explicit Consent Required</div>
              <p>
                By proceeding, you grant explicit consent to collect and process your biometric ECG telemetry in real time.
                <br /><br />
                <strong>Privacy Guarantee:</strong> Via Asynchronous Federated Learning, your raw ECG signal never leaves your device. Only anonymous model gradient updates are transmitted — <strong>your data stays yours.</strong>
              </p>
            </div>

            <div className="consent-features">
              {[
                { icon: '🔬', title: 'HCTG-Net AI', text: 'Hybrid CNN-Transformer deep learning' },
                { icon: '⚡', title: '500 Hz Sampling', text: 'AD8232 edge ECG acquisition' },
                { icon: '🏥', title: 'FHIR R4', text: 'ABDM compatible diagnostic reports' },
                { icon: '🛡️', title: 'Federated', text: 'On-device privacy-preserving AI' },
              ].map(f => (
                <div key={f.title} className="consent-feature">
                  <span className="consent-feature-icon">{f.icon}</span>
                  <div className="consent-feature-text">
                    <strong>{f.title}</strong>{f.text}
                  </div>
                </div>
              ))}
            </div>

            <button className="consent-btn" id="consent-btn" onClick={() => setConsentGiven(true)}>
              ✓ &nbsp;I Provide Explicit Consent — Start Monitoring
            </button>
            <p className="consent-disclaimer">
              This platform complies with DPDP Act 2023 · ABDM NDHM Guidelines · ISO 27001
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════
  // MAIN DASHBOARD
  // ═══════════════════════════════════════════
  return (
    <div className="app-shell">
      <ParticleBackground />
      <div className="app-wrapper">

        {/* ── Header ── */}
        <header className="app-header anim">
          <div className="header-left">
            <div className="logo-bg">
              <ActivityIcon size={22} color="var(--cyan)" />
            </div>
            <div className="header-title-group">
              <span className="header-title">PulseAI Nexus</span>
              <span className="header-sub">Cardiac Arrhythmia Triage Platform</span>
            </div>
          </div>

          <div className="header-center">
            {/* Live clock */}
            <span className="badge badge-violet" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              🕐 {timeStr}
            </span>
          </div>

          <div className="header-right">
            <span className="badge badge-violet">
              <ShieldIcon /><span>Federated</span>
            </span>
            <span className={`badge ${connectionState === 'live' ? 'badge-cyan' : connectionState === 'connecting' ? 'badge-amber' : 'badge-rose'}`}>
              {connectionState === 'live'
                ? <><div className="badge-dot badge-dot-cyan" /><WifiIcon size={12} color="var(--cyan)" /> LIVE</>
                : connectionState === 'connecting'
                ? <><div className="badge-dot badge-dot-amber" /> Connecting</>
                : <><div className="badge-dot badge-dot-rose" /> Offline / Mock</>}
            </span>
            <span className={`badge ${leadsOff ? 'badge-rose' : 'badge-emerald'}`}>
              <CpuIcon size={12} color={leadsOff ? 'var(--rose)' : 'var(--emerald)'} />
              {leadsOff ? 'Leads Disconnected' : 'Edge Active'}
            </span>
          </div>
        </header>

        <div className="main-grid">

          {/* ═══ LEFT COLUMN ═══ */}
          <div className="left-col">

            {/* ── Patient Identity Card ── */}
            <div className="glass anim anim-d1" style={{ padding: '16px 22px' }}>
              <div className="patient-card" style={{ padding: 0, border: 'none', background: 'none', margin: 0 }}>
                <div className="patient-avatar">RK</div>
                <div className="patient-info">
                  <div className="patient-name">Rajesh Kumar, 58 yrs</div>
                  <div className="patient-meta">Male · Type 2 Diabetic · Hypertension</div>
                  <div className="patient-abha">ABHA: 14-4321-7865-1234 · Session ID: PLS-{now.getDate()}{now.getMonth()}-001</div>
                </div>
                <div className="risk-tier">
                  <span className="risk-label">Risk Tier</span>
                  <span className={`badge ${isAnomaly ? 'badge-rose' : 'badge-amber'}`} style={{fontSize:'0.75rem', padding:'5px 12px'}}>
                    {isAnomaly ? '🔴 HIGH' : '🟡 MODERATE'}
                  </span>
                </div>
              </div>
            </div>

            {/* ── ECG Live Chart ── */}
            <div className={`glass anim anim-d2 ecg-panel ${isAnomaly ? 'alert-active' : ''}`}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <div className="panel-title">Real-Time ECG Telemetry</div>
                  <div className="panel-title-big">AD8232 · 500 Hz · Lead II</div>
                </div>
                <span className="panel-chip">{isAnomaly ? 'ARRHYTHMIA ALERT' : 'TRANSMIXER-AF'}</span>
              </div>

              <div className="chart-container">
                <div className="chart-grid-overlay" />
                <div className="scanline" />
                <div className="chart-corner-label">ECG CH-1 · 25mm/s</div>
                <div className="chart-speed-label">500 smp/s · {ecgData.length} pts</div>
                <RobotAI isAnomaly={isAnomaly} />
                <Line data={chartData} options={chartOptions} />
              </div>

              {/* Digital twin overlay */}
              <div className="dt-overlay">
                <HeartPulse bpm={heartRate || 72} status={isAnomaly ? 'alert' : 'normal'} />
                <div className="dt-info">
                  <span className="dt-label">Digital Twin Sync</span>
                  <span className="dt-sub">{isAnomaly ? '⚠️ Irregular Pulse Pattern Detected' : '✓ Sinus Node Coherence — Stable'}</span>
                </div>
                <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '1.3rem', fontWeight: 800, color: isAnomaly ? 'var(--rose)' : 'var(--cyan)' }}>
                    {typeof heartRate === 'number' ? Math.round(heartRate) : '—'}
                  </div>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>BPM</div>
                </div>
              </div>

              {/* Stat cards */}
              <div className="stat-cards">
                <div className="stat-card cyan">
                  <div className="stat-label">AI Confidence</div>
                  <div className="stat-value cyan">
                    {typeof confidence === 'number' ? `${(confidence * 100).toFixed(1)}` : '—'}
                    <span className="stat-unit">%</span>
                  </div>
                </div>
                <div className="stat-card violet">
                  <div className="stat-label">Model</div>
                  <div className="stat-value violet" style={{ fontSize: '0.78rem', fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                    {modelLabel}
                  </div>
                </div>
                <div className={`stat-card ${signalQuality === 'poor' ? 'amber' : 'emerald'}`}>
                  <div className="stat-label">Signal Quality</div>
                  <div className="stat-value" style={{ color: signalQualityColor, fontSize: '1rem', textTransform: 'capitalize', marginTop: 4 }}>
                    {signalQuality}
                  </div>
                </div>
              </div>

              {/* RR-CV variability bar */}
              {typeof rrCV === 'number' && (
                <div className="rrcv-row">
                  <span className="rrcv-label">RR Variability</span>
                  <div className="rrcv-bar-bg">
                    <div
                      className="rrcv-bar-fill"
                      style={{
                        width: `${Math.min(rrCV * 200, 100)}%`,
                        background: rrCV > 0.3 ? 'var(--rose)' : 'var(--cyan)',
                      }}
                    />
                  </div>
                  <span className="rrcv-val">{rrCV.toFixed(3)}</span>
                </div>
              )}

              {/* Health stability meter */}
              <div className="stability-meter">
                <div className="stability-header">
                  <span className="stability-title">Predictive Health Stability Index</span>
                  <span className={`stability-pct ${isAnomaly ? 'danger' : ''}`}>
                    {isAnomaly ? '32%' : '98%'}
                  </span>
                </div>
                <div className="meter-track">
                  <div
                    className="meter-fill"
                    style={{
                      width: isAnomaly ? '32%' : '98%',
                      background: isAnomaly
                        ? 'linear-gradient(90deg, var(--rose), #ff6b9d)'
                        : 'linear-gradient(90deg, var(--cyan), #0ea5e9)',
                    }}
                  />
                </div>
                <div className="meter-hint">Real-time risk scoring · Cloud-GPU Federated TransMixer-AF model</div>
              </div>
            </div>
          </div>

          {/* ═══ RIGHT COLUMN ═══ */}
          <div className="right-col">

            {/* ── Triage Status ── */}
            <div className={`glass anim anim-d3 ${isAnomaly ? 'alert-active' : ''}`}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <div className="panel-title">Edge AI Triage</div>
                  <div className="panel-title-big">Clinical Decision</div>
                </div>
              </div>

              {isAnomaly ? (
                <div className="triage-alert">
                  <div className="status-icon-wrap alert">
                    <AlertIcon size={30} />
                  </div>
                  <p className="status-label-alert">⚠️ Anomaly Detected</p>
                  <div className="class-name">{diagnostic.conclusion}</div>

                  {gradCamMap && (
                    <div className="gradcam-box" style={{ width: '100%' }}>
                      <div className="gradcam-label">Grad-CAM++ Explainability</div>
                      <div className="gradcam-value">{String(gradCamMap.feature_focus)}</div>
                      <span className="gradcam-highlight">
                        {String(gradCamMap.start_ms)}ms – {String(gradCamMap.end_ms)}ms &nbsp;|&nbsp; Score: {String(gradCamMap.intensity_score)}
                      </span>
                    </div>
                  )}

                  <button className="notify-btn" id="notify-abha-btn">
                    <span>🏥</span> Push to Patient's ABHA Account
                  </button>
                </div>
              ) : (
                <div className="triage-normal">
                  <div className="status-icon-wrap">
                    <CheckIcon size={30} />
                    <div className="icon-ring" />
                  </div>
                  <p className="status-label-normal">Normal Sinus Rhythm</p>
                  <p className="status-sub">Continuous 500 Hz scan · {modelLabel}</p>
                </div>
              )}
            </div>

            {/* ── Model Info ── */}
            <div className="glass anim anim-d4">
              <div className="panel-header" style={{ marginBottom: 12 }}>
                <div className="panel-title-group">
                  <div className="panel-title">Model Registry</div>
                  <div className="panel-title-big">Inference Engine</div>
                </div>
              </div>
              {[
                { key: 'Architecture', val: 'HCTG-Net v2' },
                { key: 'Classes', val: '5 arrhythmia types' },
                { key: 'Sampling', val: '500 Hz' },
                { key: 'FHIR Version', val: 'R4' },
                { key: 'Privacy', val: 'Federated + On-device' },
              ].map(r => (
                <div key={r.key} className="model-row">
                  <span className="model-key">{r.key}</span>
                  <span className="model-val">{r.val}</span>
                </div>
              ))}
            </div>

            {/* ── FHIR Diagnostic Report ── */}
            <div className="glass anim anim-d5 fhir-panel" style={{ flex: 1 }}>
              <div className="panel-header" style={{ marginBottom: 12 }}>
                <div className="panel-title-group">
                  <div className="panel-title">ABDM DiagnosticReport</div>
                  <div className="panel-title-big">FHIR R4 Live</div>
                </div>
                <span className="panel-chip">HL7 FHIR</span>
              </div>
              <pre className="fhir-log" ref={fhirRef} />
            </div>
          </div>
        </div>

        <footer className="app-footer anim anim-d6">
          PulseAI Nexus v2.0 · DPDP Act 2023 Compliant · ABDM NDHM · Real-Time Edge AI · {new Date().getFullYear()}
        </footer>

      </div>
    </div>
  );
}

export default App;
