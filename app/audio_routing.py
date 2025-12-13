from __future__ import annotations

from enum import Enum
from typing import Optional


class AudioRoute(str, Enum):
    GLASSES = "glasses"
    PHONE_SPEAKER = "phone_speaker"
    PAIRED_DEVICE = "paired_device"  # earbuds/headset BT


def infer_audio_route_override_from_text(user_text: str) -> Optional[AudioRoute]:
    t = (user_text or "").strip().lower()
    if not t:
        return None

    # earbuds / earphones / headset
    if "use earbuds" in t or "use earphones" in t or "use headset" in t:
        return AudioRoute.PAIRED_DEVICE

    # phone speaker
    if "use phone speaker" in t or "use speaker" in t:
        return AudioRoute.PHONE_SPEAKER

    # glasses
    if "use glasses" in t:
        return AudioRoute.GLASSES

    return None
