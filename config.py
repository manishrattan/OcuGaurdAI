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

import os
import json
from typing import Dict, List, Tuple

# Helper to parse lists from env
def _parse_list(env_var: str, default: List[str]) -> List[str]:
    val = os.environ.get(env_var)
    if not val:
        return default
    return [item.strip() for item in val.split(",") if item.strip()]

# Helper to parse vendor limits from env JSON or fallback default dict
def _parse_vendor_limits() -> Dict[str, Tuple[float, float]]:
    default_limits = {
        "apple": (100.0 / 60.0, 10.0),    # rate_per_sec, burst_capacity
        "meta": (80.0 / 60.0, 10.0),
        "magic": (50.0 / 60.0, 5.0),
        "research": (200.0 / 60.0, 20.0),
        "default": (60.0 / 60.0, 10.0)
    }
    
    limits_json = os.environ.get("OCUGUARD_VENDOR_LIMITS")
    if not limits_json:
        return default_limits
    try:
        raw_limits = json.loads(limits_json)
        # Convert parsed JSON back into rate limits tuples
        parsed = {}
        for vendor, limit_vals in raw_limits.items():
            if isinstance(limit_vals, list) and len(limit_vals) == 2:
                parsed[vendor.lower()] = (float(limit_vals[0]), float(limit_vals[1]))
        # Ensure default key is always present
        if "default" not in parsed:
            parsed["default"] = default_limits["default"]
        return parsed
    except Exception:
        return default_limits


# ------------------------------------------------------------------------------
# API CONFIGURATIONS
# ------------------------------------------------------------------------------
API_HOST: str = os.environ.get("OCUGUARD_API_HOST", "0.0.0.0")
API_PORT: int = int(os.environ.get("OCUGUARD_API_PORT", "8000"))
CORS_ORIGINS: List[str] = _parse_list("OCUGUARD_CORS_ORIGINS", ["*"])

# Secure Bearer Tokens validation placeholders
# In production, verify JWTs signed with this secret
JWT_SECRET_KEY: str = os.environ.get("OCUGUARD_JWT_SECRET", "placeholder-secure-jwt-key-change-in-prod")
MOCK_AUTHORIZED_TOKENS: List[str] = _parse_list(
    "OCUGUARD_MOCK_TOKENS", 
    ["tenant_apple", "tenant_meta", "tenant_magic", "tenant_research", "tenant_default"]
)

# ------------------------------------------------------------------------------
# RATE LIMIT CONFIGURATIONS
# ------------------------------------------------------------------------------
# Custom JSON representation of vendor rate limits can be set in environment:
# e.g. OCUGUARD_VENDOR_LIMITS='{"apple": [1.67, 10.0], "meta": [1.33, 10.0]}'
VENDOR_RATE_LIMITS: Dict[str, Tuple[float, float]] = _parse_vendor_limits()


# ------------------------------------------------------------------------------
# AI ENGINE / LLM CONFIGURATIONS
# ------------------------------------------------------------------------------
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
LLM_MODEL: str = os.environ.get("OCUGUARD_LLM_MODEL", "gemini-2.5-flash")
LLM_TIMEOUT_SEC: float = float(os.environ.get("OCUGUARD_LLM_TIMEOUT", "2.0"))


# ------------------------------------------------------------------------------
# SPATIAL PATHOLOGY THRESHOLD BOUNDS (Extensible Configuration)
# ------------------------------------------------------------------------------

# 1. Retinal Gas Bubble face-down limits
RETINAL_PITCH_MIN: float = float(os.environ.get("OCUGUARD_RETINAL_PITCH_MIN", "-90.0"))
RETINAL_PITCH_MAX: float = float(os.environ.get("OCUGUARD_RETINAL_PITCH_MAX", "-55.0"))

# 2. Cataract post-op pressure limits (waist bend check)
CATARACT_PITCH_MIN: float = float(os.environ.get("OCUGUARD_CATARACT_PITCH_MIN", "-45.0"))
CATARACT_PITCH_MAX: float = float(os.environ.get("OCUGUARD_CATARACT_PITCH_MAX", "45.0"))

# 3. Glaucoma stable pressure limits
GLAUCOMA_PITCH_UPRIGHT_MIN: float = float(os.environ.get("OCUGUARD_GLAUCOMA_PITCH_MIN", "-20.0"))
GLAUCOMA_PITCH_VIOLATION_LIMIT: float = float(os.environ.get("OCUGUARD_GLAUCOMA_VIOLATION_LIMIT", "-30.0"))
GLAUCOMA_CONSECUTIVE_LOOPS: int = int(os.environ.get("OCUGUARD_GLAUCOMA_CONSECUTIVE_LOOPS", "3"))

# 4. Conservative safety fallback limits (undefined surgery)
CONSERVATIVE_PITCH_MIN: float = float(os.environ.get("OCUGUARD_CONSERVATIVE_PITCH_MIN", "-20.0"))
CONSERVATIVE_ROLL_LIMIT: float = float(os.environ.get("OCUGUARD_CONSERVATIVE_ROLL_LIMIT", "30.0"))
