from app.provider_selection import infer_ai_provider_override_from_text
from app.provider_types import AIProviderId


def test_voice_command_requires_intent_token():
    # "news eco" must NOT switch provider
    assert infer_ai_provider_override_from_text("news eco") is None


def test_voice_command_echo_alias_eco():
    assert infer_ai_provider_override_from_text("usa eco") == AIProviderId.ECHO


def test_voice_command_perplexity_italian_intent():
    assert infer_ai_provider_override_from_text("passa a perplexity") == AIProviderId.PERPLEXITY
