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
import re
from typing import Any

# Regular expression to catch UUIDs, typical auth tokens, or emails
USER_ID_PATTERN = re.compile(
    r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|'
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Pattern to capture JSON/dict fields like "user_id": "...", "transcript": "...", "telemetry": [...]
FIELD_SCRUB_PATTERNS = [
    (re.compile(r'(?i)"user_id"\s*:\s*"[^"]+"'), '"user_id": "[SCRUBBED]"'),
    (re.compile(r"(?i)'user_id'\s*:\s*'[^']+'"), "'user_id': '[SCRUBBED]'"),
    (re.compile(r'(?i)"voice_transcript"\s*:\s*"[^"]*"'), '"voice_transcript": "[SCRUBBED_BY_POLICY]"'),
    (re.compile(r"(?i)'voice_transcript'\s*:\s*'[^']*'"), "'voice_transcript': '[SCRUBBED_BY_POLICY]'"),
    (re.compile(r'(?i)"transcript"\s*:\s*"[^"]*"'), '"transcript": "[SCRUBBED_BY_POLICY]"'),
    (re.compile(r"(?i)'transcript'\s*:\s*'[^']*'"), "'transcript': '[SCRUBBED_BY_POLICY]'"),
    # Match array of numbers e.g. [-12.34, 45.67, 180.0] or nested ones
    (re.compile(r'\[\s*-?\d+(?:\.\d+)?(?:,\s*-?\d+(?:\.\d+)?)*\s*\]'), '[TELEMETRY_ARRAY_SCRUBBED]'),
]


class PIIScrubbingFilter(logging.Filter):
    """
    PII Scrubber logging filter.
    Strips and sanitizes sensitive user information, raw texts, and detailed telemetry
    to maintain a strictly stateless, privacy-preserving compliance logging database.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str):
            record.msg = str(record.msg)

        # Apply scrub patterns to the log message
        scrubbed_msg = record.msg
        
        # 1. Scrub User IDs / Email / Token patterns
        scrubbed_msg = USER_ID_PATTERN.sub("[USER_ID_SCRUBBED]", scrubbed_msg)
        
        # 2. Scrub specific JSON/dict keys and telemetry lists
        for pattern, replacement in FIELD_SCRUB_PATTERNS:
            scrubbed_msg = pattern.sub(replacement, scrubbed_msg)
            
        record.msg = scrubbed_msg
        
        # Also clean up any extra variables attached to the log if they are strings
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    arg = USER_ID_PATTERN.sub("[USER_ID_SCRUBBED]", arg)
                    for pattern, replacement in FIELD_SCRUB_PATTERNS:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args)
            
        return True


def get_scrubbed_logger(name: str = "OcuGuardAI") -> logging.Logger:
    """
    Configures and returns a logging instance equipped with the PII compliance filter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s'
        )
        handler.setFormatter(formatter)
        handler.addFilter(PIIScrubbingFilter())
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger
