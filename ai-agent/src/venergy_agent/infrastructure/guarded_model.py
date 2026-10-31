import asyncio
import time
from collections.abc import Callable

from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings


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
            raise ModelAPIError(self.model_name, "skipped after a recent failure")
        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await super().request(messages, model_settings, model_request_parameters)
        except TimeoutError as error:
            self._skip_until = self._clock() + self._cooldown_seconds
            raise ModelAPIError(self.model_name, "request timed out") from error
        except ModelAPIError:
            self._skip_until = self._clock() + self._cooldown_seconds
            raise
