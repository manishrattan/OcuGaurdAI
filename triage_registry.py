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

from typing import Any, Dict
import config

# The Triage Protocol Registry is the single source of truth for surgical recovery rules.
# Developers can define a new use case here, specifying:
# - mode: "range" (standard safe envelope) or "consecutive" (Glaucoma-style temporal checks)
# - safe pitch envelopes & violation boundaries
# - local vocal text-to-speech warnings
# - voice transcript keyword-remediation mapping
PROTOCOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "RETINAL_GAS_BUBBLE": {
        "name": "Retinal Gas Bubble Recovery",
        "mode": "range",
        "pitch_min": config.RETINAL_PITCH_MIN,
        "pitch_max": config.RETINAL_PITCH_MAX,
        "safe_message": "Retinal Gas Bubble posture compliant (Face-Down).",
        "violation_msg_template": "Retinal Gas Bubble compliance breach! Pitch: {pitch:.1f}° is above {pitch_max}°.",
        "vocal_alert": "Retinal Gas Bubble breach detected. Please lower your head immediately to maintain face-down posture.",
        "comfort_remediations": {
            "default": "[LOCAL FALLBACK] Retinal Gas Bubble: Maintain face-down posturing. Ensure forehead rest is padded and neck muscles are kept neutral.",
            "keywords": [
                {
                    "keys": ["breathe", "breath", "suffocat", "chok", "airway", "gasp", "throat"],
                    "response": "[LOCAL FALLBACK] CRITICAL COMFORT NOTICE: Airway obstruction/distress suspected. Verify lateral forehead towel roll support immediately to clear the nose and mouth while strictly preserving your face-down posture."
                },
                {
                    "keys": ["spasm", "neck", "pain", "cramp", "cramping", "stiff", "ache", "sore"],
                    "response": "[LOCAL FALLBACK] Retinal Gas Bubble Remediation: Comfort alignment triggered. Deploy the 'Triple Pillow Triangle' support (placing support pillows under the chest and hips) plus a lateral forehead roll to reduce cervical spine tension without lifting your head."
                }
            ]
        }
    },
    
    "CATARACT_POST_OP": {
        "name": "Cataract Post-Op Restrictions",
        "mode": "range",
        "pitch_min": config.CATARACT_PITCH_MIN,
        "pitch_max": config.CATARACT_PITCH_MAX,
        "safe_message": "Cataract posture compliant (Avoided sharp bending).",
        "violation_msg_template": "Cataract post-op compliance breach! Pitch: {pitch:.1f}° is outside safe range.",
        "vocal_alert": "Cataract safety breach. Avoid bending at the waist as it increases intraocular pressure. Please squat or stand upright.",
        "comfort_remediations": {
            "default": "[LOCAL FALLBACK] Cataract Post-Op: Avoid intraocular pressure hazards, do not lift heavy weights, and keep your eye shield secure.",
            "keywords": [
                {
                    "keys": ["bend", "drop", "floor", "pick up", "reach", "ground"],
                    "response": "[LOCAL FALLBACK] Cataract Safety Alert: Bending detected or mentioned. Do NOT bend at the waist to pick up objects, as it spikes intraocular pressure. Ensure you keep your head high and bend strictly at the knees (squat)."
                },
                {
                    "keys": ["night", "sleep", "rub", "scratch", "itch", "bed"],
                    "response": "[LOCAL FALLBACK] Cataract Safety Alert: Verify the rigid protective eye shield is physically taped over the surgical eye to prevent accidental rubbing while sleeping."
                }
            ]
        }
    },
    
    "GLAUCOMA_POST_OP": {
        "name": "Glaucoma Episcleral Pressure Control",
        "mode": "consecutive",
        "upright_limit": config.GLAUCOMA_PITCH_UPRIGHT_MIN,
        "violation_limit": config.GLAUCOMA_PITCH_VIOLATION_LIMIT,
        "consecutive_loops": config.GLAUCOMA_CONSECUTIVE_LOOPS,
        "safe_message": "Glaucoma posture compliant (Upright).",
        "warning_msg_template": "Glaucoma warning: Pitch: {pitch:.1f}° is below upright limit ({upright_limit}°). Consecutive low frames: {consecutive}.",
        "violation_msg_template": "Glaucoma posture breach! Pitch: {pitch:.1f}° has been below {violation_limit}° for {consecutive} consecutive polls.",
        "vocal_alert": "Glaucoma posture violation. Please sit or stand upright to normalize eye pressure.",
        "comfort_remediations": {
            "default": "[LOCAL FALLBACK] Glaucoma Post-Op: Keep head upright to maintain optimal episcleral venous pressure. Avoid leaning forward or lying down flat.",
            "keywords": [
                {
                    "keys": ["pressure", "headache", "pain", "nausea", "blur", "vision"],
                    "response": "[LOCAL FALLBACK] Glaucoma Pressure Alert: Increased pressure symptoms reported. Verify upright neutral alignment immediately. Contact your ophthalmologist if symptoms persist."
                }
            ]
        }
    },
    
    "CONSERVATIVE_FALLBACK": {
        "name": "Conservative Safety Shield",
        "mode": "fallback",
        "pitch_min": config.CONSERVATIVE_PITCH_MIN,
        "roll_limit": config.CONSERVATIVE_ROLL_LIMIT,
        "safe_message": "Conservative safety shield compliant.",
        "violation_msg_template": "Conservative Shield violation! Pitch: {pitch:.1f}° or Roll: {roll:.1f}° deviated too far.",
        "vocal_alert": "Safety alert. Large angular deviation detected. Please return to a neutral upright posture.",
        "comfort_remediations": {
            "default": "[LOCAL FALLBACK] Conservative Safety Bias: Stabilize your posture, avoid rapid rotational movements, and maintain a neutral upright gaze."
        }
    }
}
