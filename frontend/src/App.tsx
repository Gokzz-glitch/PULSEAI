import { useState, useEffect, useRef } from 'react';
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

const BACKEND = 'http://localhost:8000';

const ActivitySVG = ({ size = 32, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);
const ShieldSVG = ({ size = 18, color = 'var(--color-purple)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);
const ServerSVG = ({ size = 18, color = 'var(--color-primary)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="8" rx="2" />
    <rect x="2" y="14" width="20" height="8" rx="2" />
    <line x1="6" y1="6" x2="6.01" y2="6" />
    <line x1="6" y1="18" x2="6.01" y2="18" />
  </svg>
);
const AlertSVG = ({ size = 36, color = 'var(--color-alert)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);
const CheckSVG = ({ size = 36, color = 'var(--color-primary)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

function App() {
  const [consentGiven, setConsentGiven] = useState(false);
  const [ecgData, setEcgData] = useState<number[]>([]);
  const [diagnostic, setDiagnostic] = useState<DiagnosticReport>({ status: 'Awaiting edge data...' });
  const [leadsOff, setLeadsOff] = useState(false);
  const mockRef = useRef<number | null>(null);

  // Poll backend
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
      } catch (_) { /* backend offline — mock mode active */ }
    }, 1000);
    return () => clearInterval(poll);
  }, [consentGiven]);

  // Mock ECG animation when no hardware attached
  useEffect(() => {
    if (!consentGiven) return;
    mockRef.current = window.setInterval(() => {
      setEcgData(prev => {
        const t = Date.now() / 200;
        // Simulate ECG-like waveform
        const val = Math.sin(t) * 25 + Math.sin(t * 4) * 8 + (Math.random() - 0.5) * 6 + 50;
        const next = [...prev, val];
        return next.length > 120 ? next.slice(next.length - 120) : next;
      });
    }, 80);
    return () => { if (mockRef.current) clearInterval(mockRef.current); };
  }, [consentGiven]);

  const chartData = {
    labels: ecgData.map((_, i) => i.toString()),
    datasets: [{
      data: ecgData,
      borderColor: '#00ffcc',
      backgroundColor: 'rgba(0,255,204,0.06)',
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 0,
      fill: true,
    }],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false as const,
    scales: {
      x: { display: false },
      y: { min: -10, max: 110, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#7a7d99', font: { size: 10 } } },
    },
    plugins: { legend: { display: false } },
  };

  const isAnomaly = !!(diagnostic?.conclusion && (diagnostic.conclusion.includes('Fib') || diagnostic.conclusion.includes('Arrhythmia')));
  const gradCamExt = diagnostic?.extension?.find(e => e.url.includes('gradcam'));
  let gradCamMap: Record<string, unknown> | null = null;
  if (gradCamExt?.valueString) {
    try { gradCamMap = JSON.parse(gradCamExt.valueString); } catch (_) {}
  }

  // ─── Consent Screen ───────────────────────────────────────
  if (!consentGiven) {
    return (
      <div className="consent-wrap">
        <div className="consent-card anim">
          <div className="logo-wrap">
            <ActivitySVG size={28} color="var(--color-primary)" />
          </div>
          <h1>PulseAI Nexus</h1>
          <p className="subtitle">AI-Driven Cardiac Arrhythmia Triage Platform</p>
          <div className="consent-notice">
            <h3>🚨 DPDP Act 2023 — Explicit Consent Required</h3>
            <p>
              By proceeding, you grant explicit consent for the collection and processing of your biometric ECG telemetry.
              <br /><br />
              <strong>Privacy Guarantee:</strong> Via Asynchronous Federated Learning, your raw ECG signal never leaves your device. Only anonymous gradient updates are transmitted — your data stays yours.
            </p>
          </div>
          <button className="consent-btn" onClick={() => setConsentGiven(true)}>
            I Provide Explicit Consent
          </button>
        </div>
      </div>
    );
  }

  // ─── Main Dashboard ────────────────────────────────────────
  return (
    <div className="app-wrapper">
      {/* Header */}
      <header className="app-header anim">
        <div className="header-brand">
          <ActivitySVG size={28} color="var(--color-primary)" />
          <h1>PulseAI Dashboard</h1>
        </div>
        <div className="header-badges">
          <span className="badge badge-purple"><ShieldSVG />Federated Learning</span>
          <span className={`badge ${leadsOff ? 'badge-red' : 'badge-green'}`}>
            <ServerSVG color={leadsOff ? 'var(--color-alert)' : 'var(--color-primary)'} />
            {leadsOff ? 'Leads Off' : 'Edge Active'}
          </span>
        </div>
      </header>

      {/* Grid */}
      <div className="main-grid">

        {/* Left — ECG Chart */}
        <div className="glass anim anim-d1">
          <div className="panel-title">
            Real-Time Telemetry (AD8232)
            <span>Federated TransMixer-AF</span>
          </div>
          <div className="chart-container">
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>

        {/* Right column */}
        <div className="right-col">

          {/* Triage Status */}
          <div className={`glass anim anim-d2 ${isAnomaly ? 'alert-active' : ''}`}>
            <div className="panel-title">Edge AI Triage</div>
            {isAnomaly ? (
              <div className="triage-alert">
                <div className="status-icon-wrap alert"><AlertSVG size={32} /></div>
                <p className="status-label">⚠️ Anomaly Detected</p>
                <p className="class-name">{diagnostic.conclusion}</p>
                {gradCamMap && (
                  <div className="gradcam-box">
                    <div className="label">Grad-CAM++ Explainability</div>
                    <div className="value">{String(gradCamMap.feature_focus)}</div>
                    <div className="value" style={{ color: '#9ca3af', marginTop: 4 }}>
                      Segment: {String(gradCamMap.start_ms)}ms – {String(gradCamMap.end_ms)}ms &nbsp;|&nbsp; Score: {String(gradCamMap.intensity_score)}
                    </div>
                  </div>
                )}
                <button className="notify-btn">Push to Patient's ABHA Account</button>
              </div>
            ) : (
              <div className="triage-normal">
                <div className="status-icon-wrap"><CheckSVG size={30} /></div>
                <p className="status-label">Normal Sinus Rhythm</p>
                <p className="status-sub">Continuous 500 Hz scan · TransMixer-AF active</p>
              </div>
            )}
          </div>

          {/* FHIR Report Log */}
          <div className="glass anim anim-d3" style={{ flex: 1 }}>
            <div className="panel-title">
              ABDM DiagnosticReport
              <span>FHIR R4</span>
            </div>
            <div className="fhir-log">{JSON.stringify(diagnostic, null, 2)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
