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
import re
import time
from typing import Optional
from scrubber_logger import get_scrubbed_logger
import config

logger = get_scrubbed_logger("OcuGuardAI.AIEngine")

# Try to import LangChain and Google GenAI packages.
# If they are not present, we will gracefully trigger the Failure Cascade.
try:
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain or langchain-google-genai libraries not available. Defaulting to Failure Cascade.")


class AIEngine:
    """
    LangChain-orchestrated inference engine with zero-latency deterministic failure cascade.
    """
    
    def __init__(self, api_key: Optional[str] = None, timeout_sec: Optional[float] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.timeout_sec = timeout_sec or config.LLM_TIMEOUT_SEC
        self.llm = None
        
        if LANGCHAIN_AVAILABLE and self.api_key:
            try:
                # Initialize Gemini LLM with config parameters
                self.llm = ChatGoogleGenerativeAI(
                    model=config.LLM_MODEL,
                    google_api_key=self.api_key,
                    temperature=0.1,
                    timeout=self.timeout_sec
                )
                logger.info(f"LangChain Gemini AI engine initialized successfully with model: {config.LLM_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}. Fallback active.")
        else:
            logger.info("AIEngine starting in deterministic local-only mode (Failure Cascade Default).")

    def evaluate_comfort_remediation(
        self, 
        surgery_type: str, 
        pitch_deg: float, 
        roll_deg: float, 
        voice_transcript: Optional[str],
        simulate_failure: bool = False
    ) -> tuple[str, bool]:
        """
        Parses the voice transcript and spatial posture to suggest comfort hacks.
        Returns:
            tuple: (comfort_remediation_text, is_fallback_triggered)
        """
        if not voice_transcript or not voice_transcript.strip():
            return "No voice input captured. Posture compliance active.", False

        # If simulation flag is set, bypass AI entirely to test Failure Cascade
        if simulate_failure:
            logger.warning("Simulation Trigger: Bypassing AI layer. Initiating Failure Cascade.")
            return self._run_local_keyword_matcher(surgery_type, voice_transcript), True

        # Check if LLM is initialized and available
        if self.llm is None or not LANGCHAIN_AVAILABLE:
            logger.warning("AI network/service unavailable. Bypassing AI layer. Initiating Failure Cascade.")
            return self._run_local_keyword_matcher(surgery_type, voice_transcript), True

        # Run AI-assisted evaluation
        try:
            start_time = time.time()
            prompt = PromptTemplate(
                input_variables=["surgery_type", "pitch", "roll", "voice_transcript"],
                template=(
                    "You are the OcuGuard AI Ocular Comfort Assistant.\n"
                    "Your task is to analyze a patient's voice transcript and current posture telemetry, "
                    "and suggest safe comfort remediations (comfort hacks) that do NOT violate their recovery posture guidelines.\n\n"
                    "Strict Recovery Guidelines:\n"
                    f"1. RETINAL_GAS_BUBBLE: Patient MUST maintain face-down posture (pitch {config.RETINAL_PITCH_MIN} to {config.RETINAL_PITCH_MAX} deg). "
                    "If they report neck spasms or breathing difficulty, append the 'Triple Pillow Triangle' comfort configuration "
                    "(chest/hip pillow support with a lateral forehead towel roll to clear the airway).\n"
                    f"2. CATARACT_POST_OP: Patient must avoid bending (pitch < {config.CATARACT_PITCH_MIN}). Remind them of pressure hazards and "
                    "night protective shield verification.\n"
                    f"3. GLAUCOMA_POST_OP: Upright posture (pitch > {config.GLAUCOMA_PITCH_UPRIGHT_MIN}) must be maintained to keep episcleral pressure stable.\n"
                    "4. NEVER suggest any posture or action that violates their target envelopes.\n\n"
                    "Patient Context:\n"
                    "- Surgery Type: {surgery_type}\n"
                    "- Current Telemetry: Pitch {pitch}°, Roll {roll}°\n"
                    "- Voice Transcript: \"{voice_transcript}\"\n\n"
                    "Output only a concise, clear comfort remediation instruction (under 80 words) suitable for text-to-speech. "
                    "Do not include code blocks, greetings, or meta-commentary."
                )
            )
            
            # Formulate langchain invoke
            chain = prompt | self.llm
            response = chain.invoke({
                "surgery_type": surgery_type,
                "pitch": f"{pitch_deg:.1f}",
                "roll": f"{roll_deg:.1f}",
                "voice_transcript": voice_transcript
            })
            
            elapsed = time.time() - start_time
            logger.info(f"AI Comfort inference completed in {elapsed:.3f}s.")
            
            remediation = response.content.strip()
            # Safety check: if response is empty, trigger fallback
            if not remediation:
                raise ValueError("LLM returned empty content")
                
            return remediation, False

        except Exception as err:
            logger.error(f"Inference exception encountered: {err}. Executing Failure Cascade fallback.")
            return self._run_local_keyword_matcher(surgery_type, voice_transcript), True

    def _run_local_keyword_matcher(self, surgery_type: str, transcript: str) -> str:
        """
        Deterministic, local keyword/threshold matcher to run when the AI layer is bypassed or drops.
        Queries the dynamic triage_registry.py definitions.
        """
        import triage_registry
        
        s_key = surgery_type.upper()
        if s_key not in triage_registry.PROTOCOL_REGISTRY:
            s_key = "CONSERVATIVE_FALLBACK"
            
        rule = triage_registry.PROTOCOL_REGISTRY[s_key]
        remediations_cfg = rule.get("comfort_remediations", {})
        t_lower = transcript.lower()

        # Iterate over configured keyword maps
        for item in remediations_cfg.get("keywords", []):
            keys = item.get("keys", [])
            response = item.get("response")
            if any(k in t_lower for k in keys):
                return response

        # Default remediation when no keywords match
        return remediations_cfg.get("default", "[LOCAL FALLBACK] Maintain standard posture compliance protocol.")
