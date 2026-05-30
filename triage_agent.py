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

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import config


class SurgeryType(str, Enum):
    RETINAL_GAS_BUBBLE = "RETINAL_GAS_BUBBLE"
    CATARACT_POST_OP = "CATARACT_POST_OP"
    GLAUCOMA_POST_OP = "GLAUCOMA_POST_OP"
    CONSERVATIVE_FALLBACK = "CONSERVATIVE_FALLBACK"


class TelemetryFrame(BaseModel):
    """
    Validation schema representing a single orientation telemetry reading from the wearable IMU.
    """
    pitch_deg: float = Field(
        ..., 
        description="Pitch angle in degrees. Upwards is positive, downwards is negative.",
        ge=-180.0, 
        le=180.0
    )
    roll_deg: float = Field(
        ..., 
        description="Roll angle in degrees. Leftward roll is negative, rightward is positive.",
        ge=-180.0, 
        le=180.0
    )
    yaw_deg: float = Field(
        0.0, 
        description="Yaw angle in degrees. Directional heading.",
        ge=-360.0, 
        le=360.0
    )


class TriageRequest(BaseModel):
    """
    API payload for triage. Ingests patient context, current telemetry, history, and voice stream transcript.
    """
    surgery_type: str = Field(
        ..., 
        description="The type of surgical ocular recovery protocol."
    )
    current_telemetry: TelemetryFrame = Field(
        ..., 
        description="Latest IMU frame from the wearable."
    )
    telemetry_history: Optional[List[TelemetryFrame]] = Field(
        default=None, 
        description="Historical IMU frames for temporal threshold matching (e.g. Glaucoma consecutive loop validation)."
    )
    voice_transcript: Optional[str] = Field(
        default=None, 
        description="Raw voice transcript captured from the headset microphone."
    )
    simulate_llm_failure: Optional[bool] = Field(
        default=False,
        description="Forced bypass of LLM service to execute and test local deterministic failure cascade."
    )


class TriageResponse(BaseModel):
    """
    High-priority serialized response block containing evaluation results and safety remediation actions.
    """
    status: str = Field(
        ..., 
        description="Overall evaluation status: SAFE, WARNING, VIOLATION, or SYSTEM_ERROR"
    )
    safe: bool = Field(
        ..., 
        description="Boolean safety indicator. False represents unsafe positioning or threshold breaches."
    )
    message: str = Field(
        ..., 
        description="Deterministic triage message."
    )
    vocal_alert: Optional[str] = Field(
        default=None, 
        description="Text-to-speech compatible warning message."
    )
    comfort_remediation: Optional[str] = Field(
        default=None, 
        description="Socio-comfort adjustment tip (LLM generated or fallback keyword matched)."
    )
    breach_counters: int = Field(
        default=0, 
        description="Number of violations recorded in the current telemetry window."
    )
    execution_metrics: dict = Field(
        default_factory=dict, 
        description="Stateless performance metrics (e.g. processing time, fallback status)."
    )


class SpatialEvaluationEngine:
    """
    Algorithmic triage class executing zero-latency, deterministic geometric evaluation
    driven dynamically by rules defined in triage_registry.py.
    """
    
    @staticmethod
    def evaluate_protocol(
        protocol_key: str, 
        current: TelemetryFrame, 
        history: Optional[List[TelemetryFrame]] = None
    ) -> tuple[str, bool, str, Optional[str]]:
        """
        Dynamically evaluates compliance rules for any protocol registered in triage_registry.
        Falls back to CONSERVATIVE_FALLBACK if the protocol is unknown.
        """
        import triage_registry
        
        reg_key = protocol_key.upper()
        if reg_key not in triage_registry.PROTOCOL_REGISTRY:
            reg_key = "CONSERVATIVE_FALLBACK"
            
        rule = triage_registry.PROTOCOL_REGISTRY[reg_key]
        mode = rule["mode"]
        pitch = current.pitch_deg
        roll = current.roll_deg
        
        if mode == "range":
            p_min = rule["pitch_min"]
            p_max = rule["pitch_max"]
            is_safe = p_min <= pitch <= p_max
            
            if is_safe:
                return "SAFE", True, rule["safe_message"], None
            else:
                msg = rule["violation_msg_template"].format(pitch=pitch, pitch_min=p_min, pitch_max=p_max)
                return "VIOLATION", False, msg, rule["vocal_alert"]
                
        elif mode == "consecutive":
            upright = rule["upright_limit"]
            violation_limit = rule["violation_limit"]
            limit_loops = rule["consecutive_loops"]
            
            if pitch > upright:
                return "SAFE", True, rule["safe_message"], None
                
            if pitch < violation_limit:
                consecutive_below = 1
                if history:
                    for past_frame in reversed(history):
                        if past_frame.pitch_deg < violation_limit:
                            consecutive_below += 1
                        else:
                            break
                            
                if consecutive_below >= limit_loops:
                    msg = rule["violation_msg_template"].format(pitch=pitch, violation_limit=violation_limit, consecutive=consecutive_below)
                    return "VIOLATION", False, msg, rule["vocal_alert"]
                else:
                    msg = rule["warning_msg_template"].format(pitch=pitch, upright_limit=upright, consecutive=consecutive_below)
                    alert_msg = "Caution: You are leaning too far back or down. Please return to an upright position."
                    return "WARNING", False, msg, alert_msg
            else:
                msg = f"Glaucoma warning: Pitch: {pitch:.1f}° is below upright limit ({upright}°)."
                alert_msg = "Caution: You are tilting your head down. Please raise your head upright."
                return "WARNING", False, msg, alert_msg
                
        else: # fallback or fallback range
            p_min = rule["pitch_min"]
            r_lim = rule["roll_limit"]
            
            pitch_safe = pitch > p_min
            roll_safe = -r_lim <= roll <= r_lim
            
            if pitch_safe and roll_safe:
                return "SAFE", True, rule["safe_message"], None
                
            reasons = []
            if not pitch_safe:
                reasons.append(f"Pitch: {pitch:.1f}° <= {p_min}°")
            if not roll_safe:
                reasons.append(f"Roll deviation: {roll:.1f}° outside [-{r_lim}°, {r_lim}°]")
                
            msg = f"Conservative Shield violation! Reasons: {', '.join(reasons)}."
            return "VIOLATION", False, msg, rule["vocal_alert"]

    def process_triage(self, request: TriageRequest) -> TriageResponse:
        """
        Executes dynamic mathematical checks based on the configured registry protocol.
        """
        surgery = request.surgery_type.upper()
        current = request.current_telemetry
        history = request.telemetry_history
        
        status, safe, message, vocal_alert = self.evaluate_protocol(surgery, current, history)
            
        # Calculate breach counter based on historical envelope breaches
        breach_count = 0
        if not safe:
            breach_count += 1
        if history:
            import triage_registry
            rule = triage_registry.PROTOCOL_REGISTRY.get(surgery, triage_registry.PROTOCOL_REGISTRY["CONSERVATIVE_FALLBACK"])
            mode = rule["mode"]
            for frame in history:
                if mode == "range":
                    if not (rule["pitch_min"] <= frame.pitch_deg <= rule["pitch_max"]):
                        breach_count += 1
                elif mode == "consecutive":
                    if frame.pitch_deg < rule["violation_limit"]:
                        breach_count += 1
                else:
                    if not (frame.pitch_deg > rule["pitch_min"] and -rule["roll_limit"] <= frame.roll_deg <= rule["roll_limit"]):
                        breach_count += 1

        return TriageResponse(
            status=status,
            safe=safe,
            message=message,
            vocal_alert=vocal_alert,
            breach_counters=breach_count,
            execution_metrics={
                "spatial_check": "success",
                "rules_evaluated": [surgery]
            }
        )
