# OcuGuard AI Telemetry Middleware Engine

OcuGuard AI is a high-availability, multitenant cloud middleware engine designed for real-time spatial ocular triage. Ingesting IMU pitch/roll/yaw telemetry and voice transcripts from connected wearables (smart glasses, VR headsets, mobile applications), it evaluates patient posture compliance for post-surgical recovery.

## 🎥 Project Demonstration

<p align="center">
  <video src="Demo/OcuGaurdAI.mp4" width="100%" controls>
    Your browser does not support the video tag.
  </video>
  
</p><img width="1820" height="837" alt="2" src="https://github.com/user-attachments/assets/2167440b-a23c-4b1c-afce-c6b43ee42b01" />
<img width="1820" height="837" alt="1" src="https://github.com/user-attachments/assets/ae3a0679-b40f-4968-9422-3b4fdce25004" />




---

## Key Features

1.  **Stateless API Routing Gateway**: Built on FastAPI to handle high-concurrency ingestion streams from hardware endpoints.
2.  **Dynamic Triage Protocol Registry**: Consolidates all pathology boundaries, alert templates, and voice keywords in one config file ([triage_registry.py](triage_registry.py)) to make adding new surgery types completely code-free.
3.  **LangChain Google Gemini Integration**: Utilizes Gemini to extract patient comfort hacks without breaching clinical envelopes.
4.  **Deterministic Failure Cascade**: Bypasses the AI layer instantly if API timeouts or network drops occur, defaulting to a local keyword regex matcher to preserve patient safety.
5.  **PII-Scrubbing Logger**: Restricts raw user IDs, emails, telemetry coordinate vectors, and voice transcript files from logging targets to maintain a stateless privacy footprint.
6.  **Token-Bucket Rate Limiter**: Enforces thread-safe in-memory rate limiting mapped to specific hardware vendor profiles.
7.  **3D Simulation Dashboard**: Serves a premium visual simulation environment featuring Three.js rotating glasses, sliders, preset transcripts, and TTS (text-to-speech) voice alerts.

---

## Directory Structure

```text
OcuGuardAI/
├── .env.example              # Template configuration for production onboarding
├── app.py                    # Main FastAPI application gateway & dashboard server
├── config.py                 # 12-factor environmental variables parser
├── triage_registry.py        # Central configuration registry for clinical rules
├── triage_agent.py           # Pydantic schemas and spatial geometry engine
├── ai_engine.py              # LangChain integration & local fallback keywords matcher
├── scrubber_logger.py        # PII-scrubbing console logging filter
├── requirements.txt          # Project dependencies (FastAPI, LangChain, PyTest, etc.)
├── spec.md                   # Full system API and pathology specs
├── templates/
│   └── index.html            # Premium 3D Three.js simulation dashboard page
└── tests/
    └── test_triage.py        # Complete automated test suite
```

---

## Getting Started

### 1. Install Dependencies
Clone this repository, navigate to the directory, and install:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Settings
Copy the template `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open the `.env` file and insert your API key:
```env
GEMINI_API_KEY=YOUR_SECURE_GEMINI_API_KEY_HERE
```

### 3. Run the Middleware API and Dashboard
```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:8000/
```

---

## Centralized Triage Registration

To configure a new triage surgical protocol, add an entry to the `PROTOCOL_REGISTRY` dictionary in [triage_registry.py](triage_registry.py):

```python
"MY_NEW_SURGERY": {
    "name": "My Custom Pathology Recovery Directive",
    "mode": "range",          # "range" for simple bounds, "consecutive" for state polling loops
    "pitch_min": -30.0,
    "pitch_max": 30.0,
    "safe_message": "Safe orientation maintained.",
    "violation_msg_template": "Breach detected! Pitch: {pitch:.1f}° is outside safe range.",
    "vocal_alert": "Please return your head orientation to the target safe zone.",
    "comfort_remediations": {
        "default": "[LOCAL FALLBACK] Stabilize alignment and avoid rapid tilts.",
        "keywords": [
            {
                "keys": ["spasm", "cramp", "pain"],
                "response": "[LOCAL FALLBACK] Muscle spasm alert. Place hot compress on neck."
            }
        ]
    }
}
```
The spatial engine and the LangChain AI assistant will automatically ingest and validate the custom pathology rule.

---

## Executing the Test Suite

Run the complete test suite:
```bash
python -m pytest tests/test_triage.py -v
```

---

## Open-Source Dual Licensing

OcuGuard AI protects its core architectural integrity from silent commercialization via a strict dual-licensing scheme:

*   **The Open-Source Pipeline (AGPLv3)**: Completely free for open-source engineers, researchers, and individual patients. However, if integrated into a commercial network or closed-source application, you are legally obligated to release the *entire application source code* to the public.
*   **The Commercial Wearable & Enterprise Gate**: Hardware manufacturers, smart glasses ecosystems, and proprietary telehealth developers looking to avoid the AGPLv3 copyleft mandate **are strictly required to seek explicit permission or arrange a proprietary license** before executing this logic.
