from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import get_client, observe

    class LangfuseContext:
        def update_current_trace(self, **kwargs: Any) -> None:
            get_client().update_current_trace(**kwargs)

        def update_current_observation(self, **kwargs: Any) -> None:
            client = get_client()
            metadata = kwargs.pop("metadata", None)
            usage_details = kwargs.pop("usage_details", None)
            if metadata is not None or kwargs:
                client.update_current_span(metadata=metadata, **kwargs)
            if usage_details is not None:
                client.update_current_generation(usage_details=usage_details)

    langfuse_context = LangfuseContext()

except Exception:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyContext:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_observation(self, **kwargs: Any) -> None:
            return None

    langfuse_context = _DummyContext()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
