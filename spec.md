# OcuGuard AI Telemetry Middleware - System Specification

**Version:** 1.0.0  
**License:** Dual-Licensed (AGPLv3 / Commercial)  
**Status:** Production Ready  

---

## 1. System Overview

OcuGuard AI is a stateless Python-based REST API designed to act as an edge-ingestion node. It processes hardware payloads (smart glasses, AR/VR headsets, mobile applications), runs deterministic spatial compliance checks, and interfaces with LangChain-orchestrated LLM models (Google Gemini) to generate comfort-remediation instructions without compromising clinical envelopes.

---

## 2. API Endpoints

### 2.1 Process Telemetry Frame

- **URL**: `/api/v1/telemetry`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Authentication**: Stateless bearer token verification. Active mock tokens include: `tenant_apple`, `tenant_meta`, `tenant_magic`, `tenant_research`.

#### Request Payload (`TriageRequest`)
```json
{
  "surgery_type": "RETINAL_GAS_BUBBLE",
  "current_telemetry": {
    "pitch_deg": -72.0,
    "roll_deg": 0.0,
    "yaw_deg": 0.0
  },
  "telemetry_history": [
    {
      "pitch_deg": -74.0,
      "roll_deg": 2.0,
      "yaw_deg": 1.0
    }
  ],
  "voice_transcript": "My neck is starting to feel stiff and spasming.",
  "simulate_llm_failure": false
}
```

#### Response Structure (`TriageResponse`)
```json
{
  "status": "SAFE",
  "safe": true,
  "message": "Retinal Gas Bubble posture compliant (Face-Down).",
  "vocal_alert": null,
  "comfort_remediation": "[LOCAL FALLBACK] Retinal Gas Bubble Remediation: Comfort alignment triggered...",
  "breach_counters": 0,
  "execution_metrics": {
    "spatial_check": "success",
    "rules_evaluated": ["RETINAL_GAS_BUBBLE"],
    "tenant": "meta",
    "latency_sec": 0.0012,
    "ai_failure_cascade": true
  }
}
```

---

## 3. Spatial Compliance Protocols

Pathology envelopes and rule checks are defined centrally in `triage_registry.py`.

### 3.1 RETINAL_GAS_BUBBLE
- **Clinical Directive**: Keep gas bubble locked in position via face-down posturing.
- **Safe Envelope**: `pitch_deg` strictly between `-90.0°` and `-55.0°`.
- **Violation Boundary**: `pitch_deg > -55.0°` or `pitch_deg < -90.0°`.
- **Remediation Trigger**: If transcripts contain muscle/tension indicators ("spasm", "pain", "cramp", "stiff") or breathing indicators ("breathe", "airway"), triggers specialized support pillow mapping.

### 3.2 CATARACT_POST_OP
- **Clinical Directive**: Prevent structural lens dislocation and intraocular pressure spikes.
- **Safe Envelope**: `pitch_deg` strictly between `-45.0°` and `45.0°`.
- **Violation Boundary**: `pitch_deg < -45.0°` (bending hazard) or `pitch_deg > 45.0°`.
- **Remediation Trigger**: Triggers warning regarding bending constraints or nighttime shield tape reminders on sleep keywords.

### 3.3 GLAUCOMA_POST_OP
- **Clinical Directive**: Maintain optimal upright posture to avoid venous backpressure.
- **Safe Envelope**: Neutral upright orientation (`pitch_deg > -20.0°`).
- **Violation Boundary**: `pitch_deg < -30.0°` sustained consecutively across `consecutive_loops` (default: `3`) polling frames.

### 3.4 Conservative Fallback Shield
- **Clinical Directive**: Protect patient for undefined surgery types.
- **Safe Envelope**: Upright tilt (`pitch_deg > -20.0°`) and low lateral roll deviation (`-30.0° <= roll_deg <= 30.0°`).

---

## 4. Rate-Limiting Matrices
Rate limits are checked per hardware vendor profile using an in-memory Token Bucket:
- `apple`: 100 requests / minute, burst capacity 10.
- `meta`: 80 requests / minute, burst capacity 10.
- `magic`: 50 requests / minute, burst capacity 5.
- `research`: 200 requests / minute, burst capacity 20.
- `default`: 60 requests / minute, burst capacity 10.

If breached, returns `429 Too Many Requests` with a `Retry-After: <seconds>` header.

---

## 5. Exception Handling & Failure Cascade
If the Google Gemini AI network drops or times out (`OCUGUARD_LLM_TIMEOUT` - default: `2.0s`), the system initiates the **Failure Cascade**. It bypasses the AI layer and runs the local keyword dictionary match in `triage_registry.py` to compile clinical advice instantly.
If a critical system runtime crash occurs, a global handler catches it and returns a safe JSON payload with a `SYSTEM_ERROR` flag and a high-priority, text-to-speech-compatible alert.
