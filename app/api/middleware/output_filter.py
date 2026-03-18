# app/api/middleware/output_filter.py
import logging

logger = logging.getLogger(__name__)

try:
    from guardrails import Guard
    from guardrails.hub import ToxicLanguage, SecretsPresent, DetectPII

    guard = Guard().use_many(
        ToxicLanguage(on_fail="exception"),
        SecretsPresent(on_fail="exception"),
        DetectPII(
            pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN"],
            on_fail="fix",
        ),
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    logger.warning("GuardrailsAI not installed --- output filtering disabled")
    GUARDRAILS_AVAILABLE = False
    guard = None


async def validate_llm_output(text: str) -> str:
    if not GUARDRAILS_AVAILABLE or not guard:
        return text
    try:
        result = guard.parse(text)
        return result.validated_output or text
    except Exception as e:
        raise ValueError(f"LLM output failed safety validation: {e}")
