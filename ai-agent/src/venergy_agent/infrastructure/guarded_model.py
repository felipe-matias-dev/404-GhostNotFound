import asyncio
import json
import logging
import time
from collections.abc import Callable

from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings

logger = logging.getLogger("venergy_agent.model")


class GuardedModel(WrapperModel):
    def __init__(
        self,
        wrapped: Model,
        timeout_seconds: float,
        cooldown_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(wrapped)
        self._timeout_seconds = timeout_seconds
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._skip_until = 0.0

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        if self._clock() < self._skip_until:
            self._log("pulado", 0.0)
            raise ModelAPIError(self.model_name, "skipped after a recent failure")
        started = time.monotonic()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await super().request(messages, model_settings, model_request_parameters)
        except TimeoutError as error:
            self._fail("timeout", started)
            raise ModelAPIError(self.model_name, "request timed out") from error
        except ModelHTTPError as error:
            self._fail("erro_http", started, status_code=error.status_code)
            raise
        except ModelAPIError as error:
            self._fail("erro_da_api", started, error=type(error).__name__)
            raise

    def _fail(self, reason: str, started: float, **details: object) -> None:
        self._skip_until = self._clock() + self._cooldown_seconds
        self._log(reason, time.monotonic() - started, **details)

    def _log(self, reason: str, elapsed: float, **details: object) -> None:
        line = {
            "step": "modelo",
            "model": f"{self.system}:{self.model_name}",
            "reason": reason,
            "latency_ms": round(elapsed * 1000),
            **details,
        }
        logger.info(json.dumps(line, ensure_ascii=False))
