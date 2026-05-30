# ==============================================================================
# OcuGuard AI Middleware Engine - v1.0.0
# Dual-Licensed under:
# 1. GNU Affero General Public License v3 (AGPLv3) - For Open-Source Developers
# 2. Commercial / Enterprise Proprietary License - For Closed-Source Products
#
# Commercial use, proprietary distribution, or integration into commercial
# applications (including wearables) requires explicit permission and licensing
# from the Lead Architect.
# ==============================================================================

import logging
import io
import time
import pytest
from fastapi.testclient import TestClient

from triage_agent import SpatialEvaluationEngine, TelemetryFrame, TriageRequest, SurgeryType
from ai_engine import AIEngine
from scrubber_logger import get_scrubbed_logger, PIIScrubbingFilter
from app import app, limiter

client = TestClient(app)


# 1. Test Pydantic Schemas Validation
def test_telemetry_frame_validation():
    # Valid frame
    frame = TelemetryFrame(pitch_deg=-45.0, roll_deg=10.0, yaw_deg=90.0)
    assert frame.pitch_deg == -45.0
    assert frame.yaw_deg == 90.0

    # Invalid pitch boundaries
    with pytest.raises(ValueError):
        TelemetryFrame(pitch_deg=-190.0, roll_deg=0.0)
        
    with pytest.raises(ValueError):
        TelemetryFrame(pitch_deg=45.0, roll_deg=200.0)


# 2. Test Retinal Gas Bubble Rule Logic
def test_retinal_gas_bubble_logic():
    engine = SpatialEvaluationEngine()
    
    # Target: strictly between config.RETINAL_PITCH_MIN and config.RETINAL_PITCH_MAX
    # Inside boundary -> Safe
    status, safe, msg, alert = engine.evaluate_protocol(
        "RETINAL_GAS_BUBBLE", TelemetryFrame(pitch_deg=-70.0, roll_deg=0.0)
    )
    assert status == "SAFE"
    assert safe is True
    assert alert is None

    # Outside boundary -> Violation
    status, safe, msg, alert = engine.evaluate_protocol(
        "RETINAL_GAS_BUBBLE", TelemetryFrame(pitch_deg=-40.0, roll_deg=0.0)
    )
    assert status == "VIOLATION"
    assert safe is False
    assert "above" in msg
    assert alert is not None


# 3. Test Cataract Post-Op Rule Logic
def test_cataract_post_op_logic():
    engine = SpatialEvaluationEngine()
    
    # Target: strictly between config.CATARACT_PITCH_MIN and config.CATARACT_PITCH_MAX
    # Inside boundary -> Safe
    status, safe, msg, alert = engine.evaluate_protocol(
        "CATARACT_POST_OP", TelemetryFrame(pitch_deg=0.0, roll_deg=5.0)
    )
    assert status == "SAFE"
    assert safe is True

    # Below limit -> Violation (Bending hazard)
    status, safe, msg, alert = engine.evaluate_protocol(
        "CATARACT_POST_OP", TelemetryFrame(pitch_deg=-50.0, roll_deg=0.0)
    )
    assert status == "VIOLATION"
    assert safe is False
    assert "below" in msg or "outside" in msg


# 4. Test Glaucoma Post-Op Consecutive Loop Logic
def test_glaucoma_post_op_logic():
    engine = SpatialEvaluationEngine()
    
    # Target: Upright (pitch > config.GLAUCOMA_PITCH_UPRIGHT_MIN)
    # Pitch = 10 -> Safe
    status, safe, msg, alert = engine.evaluate_protocol(
        "GLAUCOMA_POST_OP", TelemetryFrame(pitch_deg=10.0, roll_deg=0.0), history=[]
    )
    assert status == "SAFE"
    assert safe is True

    # Pitch = -25 -> Warning (unsafe positioning, but not yet consecutive violation)
    status, safe, msg, alert = engine.evaluate_protocol(
        "GLAUCOMA_POST_OP", TelemetryFrame(pitch_deg=-25.0, roll_deg=0.0), history=[]
    )
    assert status == "WARNING"
    assert safe is False

    # Pitch = -35 -> Not consecutive yet, history is empty -> WARNING (1 consecutive low frame)
    status, safe, msg, alert = engine.evaluate_protocol(
        "GLAUCOMA_POST_OP", TelemetryFrame(pitch_deg=-35.0, roll_deg=0.0), history=[]
    )
    assert status == "WARNING"
    assert safe is False

    # Pitch = -35 with 2 historical frames below violation limit -> VIOLATION (3 consecutive low frames)
    history = [
        TelemetryFrame(pitch_deg=-32.0, roll_deg=0.0),
        TelemetryFrame(pitch_deg=-40.0, roll_deg=0.0)
    ]
    status, safe, msg, alert = engine.evaluate_protocol(
        "GLAUCOMA_POST_OP", TelemetryFrame(pitch_deg=-35.0, roll_deg=0.0), history=history
    )
    assert status == "VIOLATION"
    assert safe is False
    assert "consecutive polls" in msg or "consecutive" in msg


# 5. Test Conservative Fallback Shield Logic
def test_conservative_fallback_shield():
    engine = SpatialEvaluationEngine()
    
    # Target: Neutral pitch, roll in range
    status, safe, msg, alert = engine.evaluate_protocol(
        "CONSERVATIVE_FALLBACK", TelemetryFrame(pitch_deg=0.0, roll_deg=5.0)
    )
    assert status == "SAFE"
    assert safe is True

    # Roll too large -> Violation
    status, safe, msg, alert = engine.evaluate_protocol(
        "CONSERVATIVE_FALLBACK", TelemetryFrame(pitch_deg=0.0, roll_deg=-45.0)
    )
    assert status == "VIOLATION"
    assert safe is False
    assert "Roll deviation" in msg or "Conservative Shield" in msg


# 6. Test AI Fail-Safe Keyword Fallback Matcher
def test_ai_fallback_cascade_keywords():
    ai = AIEngine(api_key=None) # Forces local mode
    
    # Test Retinal Gas Bubble comfort spasm keywords
    remediation, is_fallback = ai.evaluate_comfort_remediation(
        surgery_type="RETINAL_GAS_BUBBLE",
        pitch_deg=-70.0,
        roll_deg=0.0,
        voice_transcript="I have a terrible spasm in my neck",
        simulate_failure=True
    )
    assert is_fallback is True
    assert "Triple Pillow Triangle" in remediation

    # Test Retinal Gas Bubble breathing keywords
    remediation, _ = ai.evaluate_comfort_remediation(
        surgery_type="RETINAL_GAS_BUBBLE",
        pitch_deg=-70.0,
        roll_deg=0.0,
        voice_transcript="It is so stuffy, I can't breathe",
        simulate_failure=True
    )
    assert "Airway obstruction" in remediation

    # Test Cataract Post Op bending keywords
    remediation, _ = ai.evaluate_comfort_remediation(
        surgery_type="CATARACT_POST_OP",
        pitch_deg=10.0,
        roll_deg=0.0,
        voice_transcript="I dropped my phone on the floor, going to pick it up",
        simulate_failure=True
    )
    assert "bend strictly at the knees" in remediation


# 7. Test PII Scrubber Logging Filter
def test_pii_scrubber_logging():
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    
    test_logger = logging.getLogger("TestPIILogger")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)
    test_logger.addFilter(PIIScrubbingFilter())
    
    # Test Log 1: Contains raw user_id UUID and email
    test_logger.info("Access granted to user_id: 123e4567-e89b-12d3-a456-426614174000 for email test@example.com.")
    handler.flush()
    log_output = log_capture.getvalue()
    
    assert "123e4567" not in log_output
    assert "test@example.com" not in log_output
    assert "[USER_ID_SCRUBBED]" in log_output
    
    # Reset stream
    log_capture.truncate(0)
    log_capture.seek(0)
    
    # Test Log 2: Contains raw telemetry pitch values list and voice transcript
    test_logger.info("Processing frame: {'user_id': 'alice123', 'voice_transcript': 'my neck is sore', 'telemetry': [12.34, -45.67, 0.0]}")
    handler.flush()
    log_output2 = log_capture.getvalue()
    
    assert "alice123" not in log_output2
    assert "my neck is sore" not in log_output2
    assert "12.34" not in log_output2
    assert "-45.67" not in log_output2
    assert "[SCRUBBED]" in log_output2 or "[SCRUBBED_BY_POLICY]" in log_output2
    assert "[TELEMETRY_ARRAY_SCRUBBED]" in log_output2


# 8. Test API Routing: Auth & Rate Limiting
def test_api_auth_validation():
    # Attempt without token -> 401
    resp = client.post("/api/v1/telemetry", json={
        "surgery_type": "RETINAL_GAS_BUBBLE",
        "current_telemetry": {"pitch_deg": -70.0, "roll_deg": 0.0, "yaw_deg": 0.0}
    })
    assert resp.status_code == 401
    assert "token is missing" in resp.json()["detail"]

    # Attempt with invalid token -> 401
    resp = client.post("/api/v1/telemetry", 
        headers={"Authorization": "Bearer bad_token_123"},
        json={
            "surgery_type": "RETINAL_GAS_BUBBLE",
            "current_telemetry": {"pitch_deg": -70.0, "roll_deg": 0.0, "yaw_deg": 0.0}
        }
    )
    assert resp.status_code == 401
    assert "Invalid token signature" in resp.json()["detail"]

    # Attempt with valid token -> 200
    resp = client.post("/api/v1/telemetry", 
        headers={"Authorization": "Bearer tenant_meta"},
        json={
            "surgery_type": "RETINAL_GAS_BUBBLE",
            "current_telemetry": {"pitch_deg": -70.0, "roll_deg": 0.0, "yaw_deg": 0.0}
        }
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SAFE"


def test_api_rate_limiting():
    # To isolate and force rate limit trigger quickly, we can test using a specific vendor key
    # e.g., "magic" has a lower capacity (5 tokens)
    headers = {"Authorization": "Bearer tenant_magic"}
    payload = {
        "surgery_type": "RETINAL_GAS_BUBBLE",
        "current_telemetry": {"pitch_deg": -70.0, "roll_deg": 0.0, "yaw_deg": 0.0}
    }
    
    # Consume all tokens (capacity is 5 for magic)
    for _ in range(5):
        resp = client.post("/api/v1/telemetry", headers=headers, json=payload)
        assert resp.status_code == 200
        
    # Sixth call should trigger 429 rate limit
    resp = client.post("/api/v1/telemetry", headers=headers, json=payload)
    assert resp.status_code == 429
    assert "limit exceeded" in resp.json()["message"]
    assert "Retry-After" in resp.headers
