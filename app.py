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
import time
from threading import Lock
from typing import Optional

from fastapi import FastAPI, Depends, Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

import config
from scrubber_logger import get_scrubbed_logger
from triage_agent import SpatialEvaluationEngine, TriageRequest, TriageResponse
from ai_engine import AIEngine

logger = get_scrubbed_logger("OcuGuardAI.Gateway")

# Initialize FastAPI App
app = FastAPI(
    title="OcuGuard AI Middleware Engine",
    version="1.0.0",
    description="Extensible, Edge-Agnostic Cloud Middleware API for Wearable Health Mesh"
)

# Enable CORS Protection
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Handler
security_scheme = HTTPBearer(auto_error=False)

def get_tenant_profile(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> str:
    """
    Stateless multi-tenant token validation.
    Extracts the tenant / vendor profile from Bearer credentials.
    """
    if not credentials:
        logger.warning("Unauthenticated request blocked. Missing authorization token.")
        raise HTTPException(
            status_code=401,
            detail="Authorization token is missing. Please provide a Bearer token."
        )
    
    token = credentials.credentials
    if token in config.MOCK_AUTHORIZED_TOKENS:
        vendor = token.replace("tenant_", "").lower()
        return vendor
    
    logger.warning(f"Unauthorized access attempt with invalid token signature.")
    raise HTTPException(
        status_code=401,
        detail="Invalid token signature. Unauthorized multitenant credentials."
    )


# Thread-safe in-memory Token Bucket Rate Limiter
class TokenBucketLimiter:
    def __init__(self):
        self.lock = Lock()
        self.buckets = {}
        # Load limits dynamically from config module
        self.limits = config.VENDOR_RATE_LIMITS

    def consume(self, tenant_id: str) -> tuple[bool, int]:
        """
        Consumes one token from the tenant's bucket.
        Returns:
            (is_allowed: bool, retry_after: int)
        """
        rate, capacity = self.limits.get(tenant_id, self.limits["default"])
        now = time.time()
        
        with self.lock:
            if tenant_id not in self.buckets:
                self.buckets[tenant_id] = (capacity, now)
                tokens, last_update = capacity, now
            else:
                tokens, last_update = self.buckets[tenant_id]
                
            # Replenish based on elapsed time
            elapsed = now - last_update
            replenished = tokens + elapsed * rate
            if replenished > capacity:
                replenished = capacity
                
            if replenished >= 1.0:
                self.buckets[tenant_id] = (replenished - 1.0, now)
                return True, 0
            else:
                self.buckets[tenant_id] = (replenished, now)
                needed = 1.0 - replenished
                retry_after = int(needed / rate) + 1
                return False, retry_after

limiter = TokenBucketLimiter()

# In-memory singletons
spatial_engine = SpatialEvaluationEngine()
ai_engine = AIEngine()


# Exception Handlers to ensure Deterministic Fail-Safe compliance responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught: {exc}")
    # Return high-priority TTS-compatible SYSTEM_ERROR block
    return JSONResponse(
        status_code=500,
        content={
            "status": "SYSTEM_ERROR",
            "safe": False,
            "message": "Critical system boundary error encountered. Execute recovery posture default.",
            "vocal_alert": "System error encountered. Please verify your posture manually and maintain neutral upright posture.",
            "comfort_remediation": "[FAIL-SAFE] Stabilize alignment. Avoid tilting your head until middleware is restored.",
            "breach_counters": 1,
            "execution_metrics": {
                "error_type": type(exc).__name__,
                "state": "cascade_bypass"
            }
        }
    )


# Telemetry Processing Route
@app.post("/api/v1/telemetry", response_model=TriageResponse)
async def process_telemetry(
    request_data: TriageRequest, 
    tenant: str = Depends(get_tenant_profile)
):
    start_time = time.time()
    
    # 1. Enforce strict rate-limiting per hardware vendor profile
    allowed, retry_after = limiter.consume(tenant)
    if not allowed:
        logger.warning(f"Rate limit breached for vendor: {tenant}.")
        return JSONResponse(
            status_code=429,
            content={
                "status": "SYSTEM_ERROR",
                "safe": False,
                "message": f"Strict rate limit exceeded for vendor '{tenant}'. Retry after {retry_after}s.",
                "vocal_alert": "Rate limit exceeded. Wearable pacing commands active.",
                "comfort_remediation": "[SYSTEM ALERT] Rate limit exceeded. Pacing network packets.",
                "breach_counters": 0,
                "execution_metrics": {
                    "tenant": tenant,
                    "retry_after": retry_after
                }
            },
            headers={"Retry-After": str(retry_after)}
        )
        
    # Log incoming request metadata (PII logger will automatically scrub details)
    logger.info(f"Ingested telemetry frame for Tenant: {tenant}, Surgery: {request_data.surgery_type}, Raw Transcript: '{request_data.voice_transcript}'")

    # 2. Run Spatial Triage check (Deterministic Zero-Latency Engine)
    triage_res = spatial_engine.process_triage(request_data)
    
    # 3. Process LLM comfort remediation with LangChain & Gemini
    comfort_remediation = None
    is_fallback = False
    
    if request_data.voice_transcript:
        # Evaluate comfort using LangChain, trigger Failure Cascade fallback if necessary
        comfort_remediation, is_fallback = ai_engine.evaluate_comfort_remediation(
            surgery_type=request_data.surgery_type,
            pitch_deg=request_data.current_telemetry.pitch_deg,
            roll_deg=request_data.current_telemetry.roll_deg,
            voice_transcript=request_data.voice_transcript,
            simulate_failure=request_data.simulate_llm_failure
        )
    else:
        comfort_remediation = "No voice symptoms reported."
        
    triage_res.comfort_remediation = comfort_remediation
    
    # Update performance metrics
    latency = time.time() - start_time
    triage_res.execution_metrics.update({
        "tenant": tenant,
        "latency_sec": round(latency, 4),
        "ai_failure_cascade": is_fallback
    })
    
    # Standard compliance logging (anonymized fields)
    logger.info(f"Triage complete. Status: {triage_res.status}, Safe: {triage_res.safe}, Latency: {latency:.4f}s, Fallback Cascade: {is_fallback}")
    
    return triage_res


# Serve the Premium Web Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    
    return HTMLResponse(content="<h1>OcuGuard AI Middleware Engine Dashboard - Template not found</h1>")


# Run entry point
if __name__ == "__main__":
    import uvicorn
    # Start web api on host and port specified in config
    uvicorn.run("app:app", host=config.API_HOST, port=config.API_PORT, reload=True)
