# pulseAI CDSCO Essential Principles & Technical Documentation (MOCK)

## Regulatory Classification
- **Device Description:** Single-Lead Continuous Ambulatory ECG Monitoring with AI-Driven Arrhythmia Triage.
- **Classification:** Investigational Medical Device / Clinical Decision Support System (CDSS)
- **Class:** Intended for Class B / Class C evaluation under the Medical Devices Rules, 2017 (India).

## Safety & Performance Requirements (Mock Conformity)
1. **Clinical Limitations:** Device is explicitly for rhythm anomaly detection (arrhythmia) and NOT for morphological diagnosis of structural/ischemic heart disease (e.g., STEMI).
2. **Motion Artifact Resilience:** Application employs a Hybrid CNN-Transformer model (HCTG-Net) with a Python-based preprocessing pipeline to mitigate AD8232 induced motion artifacts natively.
3. **Data Privacy:** Application incorporates explicit, DPDP 2023-compliant consent protocols before ECG data streams are initiated.
4. **Interoperability:** Analysis outputs strictly conform to the HL7 FHIR R4 standard (DiagnosticReport) aimed at M2 Sandbox Integration with India's Ayushman Bharat Digital Mission (ABDM).

## Risk Analysis Highlights
* Risk: Falsely flagging normal baseline wander as AFib. 
* Mitigation: Implementing multi-stage Python `scipy.signal` high-pass and notch filtering prior to any AI inference block.

* Risk: Data breach of sensitive health telemetry.
* Mitigation: Simulated SSL transit, minimal PII edge processing, and DB RBAC segregation for patient vs. provider dashboards.
