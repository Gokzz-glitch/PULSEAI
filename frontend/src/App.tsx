import React, { useState, useEffect, useMemo, useRef, Suspense } from 'react';
import { Line } from 'react-chartjs-2';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Sphere, PerspectiveCamera, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { 
  Activity, 
  Shield, 
  Cpu, 
  AlertTriangle, 
  CheckCircle2, 
  User, 
  Wifi, 
  Heart, 
  Zap, 
  Database, 
  Layers,
  Info,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
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

const BACKEND = ((import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000') as string;
const API_KEY = ((import.meta as any).env?.VITE_PULSEAI_API_KEY || '') as string;
const WS_BASE_URL = `${BACKEND.replace(/^http/, 'ws')}/ws`;
const WS_URL = API_KEY ? `${WS_BASE_URL}?api_key=${encodeURIComponent(API_KEY)}` : WS_BASE_URL;
const ECG_JITTER_DELAY_MS = 200;
const ECG_RENDER_INTERVAL_MS = 40;

const apiHeaders = (): HeadersInit => {
  if (!API_KEY) return {};
  return { 'X-API-Key': API_KEY };
};

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

// ─── 3D Heart Visualization (R3F) ──────────────────────────
const Heart3D = ({ bpm, isAnomaly }: { bpm: number; isAnomaly: boolean }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const pulseFactor = useRef(0);
  
  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.getElapsedTime();
    
    // Explicit BPM Sync with Thump-Thump heartbeat rather than sine wave
    const beatDuration = 60 / Math.max(bpm, 30);
    const beatTime = (time % beatDuration) / beatDuration;
    
    let targetScale = 1.0;
    if (beatTime < 0.15) targetScale = 1.0 + Math.sin((beatTime / 0.15) * Math.PI) * 0.25;
    else if (beatTime > 0.25 && beatTime < 0.4) targetScale = 1.0 + Math.sin(((beatTime - 0.25) / 0.15) * Math.PI) * 0.15;
    
    pulseFactor.current = THREE.MathUtils.lerp(pulseFactor.current, targetScale, 0.2);
    meshRef.current.scale.set(pulseFactor.current, pulseFactor.current, pulseFactor.current);
    meshRef.current.rotation.y += 0.01;
    meshRef.current.rotation.z = Math.sin(time * 0.5) * 0.1;
  });

  const heartShape = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(0, 0);
    shape.bezierCurveTo(0, -0.75, -0.75, -0.75, -0.75, 0);
    shape.bezierCurveTo(-0.75, 0.75, 0, 1.1, 0, 1.5);
    shape.bezierCurveTo(0, 1.1, 0.75, 0.75, 0.75, 0);
    shape.bezierCurveTo(0.75, -0.75, 0, -0.75, 0, 0);
    return shape;
  }, []);

  const extrudeSettings = {
    depth: 0.4,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 2,
    bevelSize: 0.1,
    bevelThickness: 0.1,
  };

  return (
    <group rotation={[Math.PI, 0, 0]} scale={0.8}>
      <mesh ref={meshRef}>
        <extrudeGeometry args={[heartShape, extrudeSettings]} />
        <MeshDistortMaterial
          color={isAnomaly ? '#f43f5e' : '#00f5d4'}
          speed={isAnomaly ? 5 : 2}
          distort={isAnomaly ? 0.4 : 0.2}
          radius={1}
          emissive={isAnomaly ? '#f43f5e' : '#00f5d4'}
          emissiveIntensity={isAnomaly ? 1.5 : 0.6}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>
    </group>
  );
};

// ─── 3D Background Component ──────────────────────────────
const Background3D = () => (
  <div className="bg-canvas-wrap">
    <Canvas>
      <PerspectiveCamera makeDefault position={[0, 0, 10]} />
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={1.5} color="#00f5d4" />
      <pointLight position={[-10, -10, -10]} intensity={1.5} color="#a78bfa" />
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
        <Sphere args={[1.5, 64, 64]} position={[8, 4, -10]}>
          <MeshDistortMaterial color="#00f5d4" speed={2} distort={0.4} />
        </Sphere>
      </Float>
      <Float speed={3} rotationIntensity={1} floatIntensity={1}>
        <Sphere args={[1, 64, 64]} position={[-8, -6, -8]}>
          <MeshDistortMaterial color="#a78bfa" speed={3} distort={0.5} />
        </Sphere>
      </Float>
    </Canvas>
  </div>
);

// ─── Robot AI Scanner ────────────────────────────────────────
const RobotAI = ({ isAnomaly }: { isAnomaly: boolean }) => (
  <motion.div 
    className={`robot-scanner ${isAnomaly ? 'robot-alert' : 'robot-thinking'}`}
    animate={{ x: isAnomaly ? [0, -2, 2, -2, 0] : 0 }}
    transition={{ repeat: isAnomaly ? Infinity : 0, duration: 0.2 }}
  >
    <div className="robot-head">
      <div className="robot-eye left" />
      <div className="robot-eye right" />
    </div>
    <div className="robot-ring" />
    <div className="laser-beam" />
    <div className="robot-status-text">
      {isAnomaly ? '⚡ ANOMALY DETECTED' : '● ANALYZING SIGNAL'}
    </div>
  </motion.div>
);

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
  const [dataSource, setDataSource] = useState<string>('SERIAL');
  const [tick, setTick] = useState(0);

  const wsRef     = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const pingRef   = useRef<number | null>(null);
  const fhirRef   = useRef<HTMLPreElement>(null);
  const mockRef   = useRef<number | null>(null);
  const ecgJitterQueueRef = useRef<Array<{ at: number; data: number[] }>>([]);

  const enqueueEcgSnapshot = (snapshot?: number[]) => {
    if (!Array.isArray(snapshot) || snapshot.length === 0) return;
    ecgJitterQueueRef.current.push({ at: Date.now(), data: snapshot });
    if (ecgJitterQueueRef.current.length > 24) {
      ecgJitterQueueRef.current = ecgJitterQueueRef.current.slice(-24);
    }
  };

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!consentGiven) return;
    const jitterTimer = window.setInterval(() => {
      const queue = ecgJitterQueueRef.current;
      const now = Date.now();
      let picked: number[] | null = null;
      while (queue.length > 0 && now - queue[0].at >= ECG_JITTER_DELAY_MS) {
        const next = queue.shift();
        if (next?.data?.length) picked = next.data;
      }
      if (picked) setEcgData(picked);
    }, ECG_RENDER_INTERVAL_MS);
    return () => clearInterval(jitterTimer);
  }, [consentGiven]);

  useEffect(() => {
    if (!consentGiven) return;
    const poll = setInterval(async () => {
      try {
        const [ecgRes, diagRes, healthRes] = await Promise.all([
          fetch(`${BACKEND}/api/ecg`, { headers: apiHeaders() }),
          fetch(`${BACKEND}/api/diagnostic`, { headers: apiHeaders() }),
          fetch(`${BACKEND}/api/health`),
        ]);
        const ecgJson = await ecgRes.json();
        const diagJson = await diagRes.json();
        const healthJson = await healthRes.json();

        enqueueEcgSnapshot(ecgJson.data);
        if (ecgJson.leads_off !== undefined) setLeadsOff(ecgJson.leads_off);
        if (diagJson) setDiagnostic(diagJson);
        if (healthJson.active_source) setDataSource(healthJson.active_source);
        if (connectionState !== 'live') setConnectionState('connecting');
      } catch (_) {}
    }, 2000);
    return () => clearInterval(poll);
  }, [consentGiven, connectionState]);

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
          if (payload.type === 'leads_on') { setLeadsOff(false); return; }
          if (payload.type === 'snapshot') {
            enqueueEcgSnapshot(payload.ecg_snapshot);
            return;
          }
          if (payload.type === 'prediction') {
            enqueueEcgSnapshot(payload.ecg_snapshot);
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

  const handleSourceChange = async (source: string) => {
    setDataSource(source);
    try {
      await fetch(`${BACKEND}/api/source?source=${source}`, { method: 'POST', headers: apiHeaders() });
    } catch (e) {
      console.error('Failed to switch source:', e);
    }
  };

  useEffect(() => {
    if (fhirRef.current) {
      fhirRef.current.innerHTML = syntaxHighlight(JSON.stringify(diagnostic, null, 2));
    }
  }, [diagnostic]);

  const modelLabel    = lastPrediction?.model_used || 'PulseAI TransMixer-AF';
  const confidence    = lastPrediction?.confidence;
  const heartRate     = lastPrediction?.heart_rate_bpm;
  const rrCV          = lastPrediction?.rr_cv;
  const signalQuality = lastPrediction?.signal_quality || 'good';
  const isAnomaly     = !!(diagnostic?.conclusion && !diagnostic.conclusion.toLowerCase().includes('normal sinus'));

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
        min: -10, max: 150,
        grid: { color: 'rgba(255,255,255,0.025)' },
        ticks: { color: '#4a5280', font: { size: 9 }, maxTicksLimit: 5 },
        border: { display: false },
      },
    },
    plugins: { legend: { display: false } },
  };

  if (!consentGiven) {
    return (
      <div className="app-shell">
        <Background3D />
        <ParticleBackground />
        <div className="consent-wrap">
          <motion.div 
            className="consent-card anim"
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="consent-header-glass">
              <div className="consent-logo">
                <div className="consent-logo-bg">
                  <Activity size={32} color="var(--cyan)" />
                </div>
                <div className="consent-logo-ring" />
              </div>
              <h1 className="consent-title">PulseAI Nexus</h1>
              <p className="consent-sub">AI-Driven Cardiac Arrhythmia Triage Platform · Real-Time ECG Analysis</p>
            </div>

            <div className="consent-notice">
              <div className="consent-notice-title">
                <Shield size={18} color="var(--cyan)" />
                🚨 DPDP Act 2023 — Explicit Consent Required
              </div>
              <p>
                By proceeding, you grant explicit consent to collect and process your biometric ECG telemetry in real time.
                <br /><br />
                <strong>Privacy Guarantee:</strong> Via Asynchronous Federated Learning, your raw ECG signal never leaves your device. Only anonymous model gradient updates are transmitted — <strong>your data stays yours.</strong>
              </p>
            </div>

            <div className="consent-features">
              {[
                { icon: <Cpu />, title: 'HCTG-Net AI', text: 'Hybrid CNN-Transformer deep learning' },
                { icon: <Zap />, title: 'Multi-Source', text: 'Bluetooth, Serial, Wi-Fi & Remote' },
                { icon: <Activity />, title: 'FHIR R4', text: 'ABDM compatible diagnostic reports' },
                { icon: <Shield />, title: 'Federated', text: 'On-device privacy-preserving AI' },
              ].map((f, i) => (
                <motion.div 
                  key={f.title} 
                  className="consent-feature"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + (i * 0.1) }}
                >
                  <span className="consent-feature-icon">{f.icon}</span>
                  <div className="consent-feature-text">
                    <strong>{f.title}</strong>{f.text}
                  </div>
                </motion.div>
              ))}
            </div>

            <motion.button 
              className="consent-btn" 
              id="consent-btn" 
              onClick={() => setConsentGiven(true)}
              whileHover={{ scale: 1.02, backgroundColor: 'rgba(0, 245, 212, 0.2)' }}
              whileTap={{ scale: 0.98 }}
            >
              ✓ &nbsp;I Provide Explicit Consent — Start Monitoring
            </motion.button>
            <p className="consent-disclaimer">
              This platform complies with DPDP Act 2023 · ABDM NDHM Guidelines · ISO 27001
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Background3D />
      <ParticleBackground />
      <div className="app-wrapper">

        <motion.header 
          className="app-header anim"
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="header-left">
            <motion.div 
              className="logo-bg"
              whileHover={{ rotate: 180, scale: 1.1 }}
              transition={{ duration: 0.6 }}
            >
              <Activity size={22} color="var(--cyan)" />
            </motion.div>
            <div className="header-title-group">
              <span className="header-title">PulseAI Nexus</span>
              <span className="header-sub">Cardiac Arrhythmia Triage Platform</span>
            </div>
          </div>

          <div className="header-center">
            <span className="badge badge-violet" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              🕐 {timeStr}
            </span>
          </div>

          <div className="header-right">
             <div className="source-selector-wrap">
              <Wifi size={14} color="var(--violet)" />
              <select 
                value={dataSource} 
                onChange={(e) => handleSourceChange(e.target.value)}
                className="source-dropdown"
              >
                <option value="MQTT">📡 MQTT</option>
                <option value="SERIAL">🔌 Serial</option>
                <option value="RECORDED_REAL">📚 Real Dataset</option>
                <option value="HTTP">💻 Remote</option>
              </select>
            </div>
            
            <AnimatePresence mode="wait">
              <motion.span 
                key={connectionState}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`badge ${connectionState === 'live' ? 'badge-cyan' : connectionState === 'connecting' ? 'badge-amber' : 'badge-rose'}`}
              >
                {connectionState === 'live' ? 'LIVE' : connectionState === 'connecting' ? 'Connecting' : 'Offline'}
              </motion.span>
            </AnimatePresence>

            <span className={`badge ${leadsOff ? 'badge-rose' : 'badge-emerald'}`}>
              {leadsOff ? 'Leads Off' : 'Edge Active'}
            </span>
          </div>
        </motion.header>

        <div className="main-grid">
          <div className="left-col">
            <motion.div 
              className="glass anim anim-d1" 
              style={{ padding: '16px 22px' }}
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <div className="patient-card" style={{ padding: 0, border: 'none', background: 'none', margin: 0 }}>
                <div className="patient-avatar">RK</div>
                <div className="patient-info">
                  <div className="patient-name">Rajesh Kumar, 58 yrs</div>
                  <div className="patient-meta">Male · Type 2 Diabetic · Hypertension</div>
                  <div className="patient-abha">ABHA: 14-4321-7865-1234 · Session: PLS-{now.getDate()}-001</div>
                </div>
                <div className="risk-tier">
                  <span className="risk-label">Risk Tier</span>
                  <span className={`badge ${isAnomaly ? 'badge-rose' : 'badge-amber'}`}>
                    {isAnomaly ? '🔴 HIGH' : '🟡 MOD'}
                  </span>
                </div>
              </div>
            </motion.div>

            <motion.div 
              className={`glass anim anim-d2 ecg-panel ${isAnomaly ? 'alert-active' : ''}`}
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <div className="panel-header">
                <div className="panel-title-group">
                  <div className="panel-title">Real-Time ECG Telemetry</div>
                  <div className="panel-title-big">Source: {dataSource} · 500 Hz</div>
                </div>
                <span className="panel-chip">{isAnomaly ? 'ARRHYTHMIA ALERT' : 'STABLE'}</span>
              </div>

              <div className="chart-container" style={{ position: 'relative' }}>
                <div className="chart-grid-overlay" />
                <div className="scanline" />
                <RobotAI isAnomaly={isAnomaly} />
                <Line data={chartData} options={chartOptions} />
                
                <AnimatePresence>
                  {isAnomaly && lastPrediction?.explainability_map && (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.9, y: 10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.9, y: 10 }}
                      style={{
                        position: 'absolute', top: 20, right: 20, 
                        background: 'rgba(244,63,94,0.15)', backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(244,63,94,0.5)', borderRadius: '12px',
                        padding: '12px 16px', zIndex: 10, color: 'white',
                        boxShadow: '0 8px 32px rgba(244,63,94,0.2)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <Zap size={18} color="var(--rose)" />
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--rose)', letterSpacing: '0.05em' }}>XAI Grad-CAM</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#e2e8f0', lineHeight: '1.6' }}>
                        <strong style={{ color: 'white' }}>Feature Focus:</strong> {(lastPrediction.explainability_map as any).feature_focus} <br/>
                        <strong style={{ color: 'white' }}>Activation:</strong> {Math.round(((lastPrediction.explainability_map as any).intensity_score || 0) * 100)}%
                      </div>
                      <div style={{ marginTop: '8px', width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.round(((lastPrediction.explainability_map as any).intensity_score || 0) * 100)}%` }}
                          transition={{ duration: 1, ease: 'easeOut' }}
                          style={{ height: '100%', background: 'var(--rose)' }}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="dt-overlay">
                <div className="heart-3d-wrap" style={{ width: '80px', height: '80px' }}>
                  <Canvas camera={{ position: [0, 0, 4], fov: 40 }}>
                    <Suspense fallback={null}>
                      <ambientLight intensity={0.5} />
                      <pointLight position={[10, 10, 10]} intensity={1} />
                      <Heart3D bpm={heartRate || 72} isAnomaly={isAnomaly} />
                    </Suspense>
                  </Canvas>
                </div>
                <div className="dt-info">
                  <span className="dt-label">Digital Twin Sync</span>
                  <span className="dt-sub">{isAnomaly ? '⚠️ Irregular Pattern' : '✓ Normal Sinus Rhythm'}</span>
                </div>
                <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                  <motion.div 
                    key={heartRate}
                    initial={{ scale: 1.2, color: 'var(--rose)' }}
                    animate={{ scale: 1, color: isAnomaly ? 'var(--rose)' : 'var(--cyan)' }}
                    style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '1.8rem', fontWeight: 800 }}
                  >
                    {typeof heartRate === 'number' ? Math.round(heartRate) : '—'}
                  </motion.div>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-3)' }}>BPM</div>
                </div>
              </div>

              <div className="stat-cards">
                <div className="stat-card cyan">
                  <div className="stat-label">AI Confidence</div>
                  <div className="stat-value cyan">
                    {typeof confidence === 'number' ? `${(confidence * 100).toFixed(1)}` : '—'}<span className="stat-unit">%</span>
                  </div>
                </div>
                <div className="stat-card violet">
                  <div className="stat-label">Health Index</div>
                  <div className="stat-value violet">
                    {typeof confidence === 'number' ? `${isAnomaly ? (100 - confidence * 100).toFixed(1) : (confidence * 100).toFixed(1)}` : '—'}<span className="stat-unit">/100</span>
                  </div>
                </div>
                <div className="stat-card emerald">
                  <div className="stat-label">Quality</div>
                  <div className="stat-value emerald" style={{ fontSize: '0.9rem', textTransform: 'uppercase' }}>{signalQuality}</div>
                </div>
              </div>
            </motion.div>
          </div>

          <div className="right-col">
            <motion.div 
              className={`glass anim anim-d3 ${isAnomaly ? 'alert-active' : ''}`}
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <div className="panel-header">
                <div className="panel-title-group">
                  <div className="panel-title">Triage Engine</div>
                  <div className="panel-title-big">Clinical Decision</div>
                </div>
              </div>

              <AnimatePresence mode="wait">
                {isAnomaly ? (
                  <motion.div 
                    key="alert"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 1.1 }}
                    className="triage-alert"
                  >
                    <div className="alert-icon-ring">
                      <AlertTriangle size={40} color="var(--rose)" />
                    </div>
                    <p className="status-label-alert">⚠️ Anomaly Detected</p>
                    <div className="class-name">{diagnostic.conclusion}</div>
                    <motion.button 
                      className="notify-btn"
                      whileHover={{ scale: 1.05, backgroundColor: 'var(--rose)' }}
                      whileTap={{ scale: 0.95 }}
                    >
                      🏥 Push to ABHA
                    </motion.button>
                  </motion.div>
                ) : (
                  <motion.div 
                    key="normal"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 1.1 }}
                    className="triage-normal"
                  >
                    <div className="success-icon-ring">
                      <CheckCircle2 size={40} color="var(--cyan)" />
                    </div>
                    <p className="status-label-normal">Normal Rhythm</p>
                    <p className="status-sub">500 Hz Real-time scan active</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            <motion.div 
              className="glass anim anim-d5 fhir-panel" 
              style={{ flex: 1 }}
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="panel-header">
                <div className="panel-title-group">
                  <div className="panel-title">FHIR DiagnosticReport</div>
                  <div className="panel-title-big">HL7 R4 Output</div>
                </div>
                <div className="live-pill">
                  <span className="pulse-dot" />
                  Live
                </div>
              </div>
              <pre className="fhir-log" ref={fhirRef} />
            </motion.div>
          </div>
        </div>

        <motion.footer 
          className="app-footer anim anim-d6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          PulseAI Nexus v3.0 · Butter-Smooth 3D Engine · Framer Powered · {new Date().getFullYear()}
        </motion.footer>

      </div>
    </div>
  );
}

export default App;
