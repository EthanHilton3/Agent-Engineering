"""Model adapter: one streamed Responses API request per round (plan §8.3).

Everything leaving this module is plain dicts: output items are converted with
`model_dump(mode="json", exclude_unset=True)` (what the SDK itself sends when given SDK objects),
so the session, the fake adapter, and history all speak one format.
"""
from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import httpx
import openai

from .config import AgentConfig
from .events import Event, ModelRetry, Notice, TextDelta, WebAction
from .pricing import Usage, cost_usd
from .workspace import CancelToken

Emit = Callable[[Event], None]

# Errors that mean "the connection broke"; retried only once the stream has started, because the
# SDK already retries connection errors, 429 and 5xx before that (max_retries=3).
RETRYABLE_STREAM_ERRORS = (httpx.TransportError, openai.APIConnectionError)
OPTIONAL_PARAMS = ("include", "prompt_cache_key")


# Max silence between stream chunks before the connection counts as stalled (then retried). High
# reasoning efforts can legitimately think for minutes before the first token. A 600 s value let one
# benchmark run sit idle for ~12 minutes.
READ_TIMEOUT_S = 120
READ_TIMEOUT_HIGH_REASONING_S = 300
HIGH_REASONING = ("high", "xhigh")


def request_timeout(reasoning: str) -> httpx.Timeout:
    read = READ_TIMEOUT_HIGH_REASONING_S if reasoning in HIGH_REASONING else READ_TIMEOUT_S
    return httpx.Timeout(read, connect=15)


class ModelError(Exception):
    def __init__(self, message: str, code: str = "model_error"):
        super().__init__(message)
        self.code = code


class Cancelled(Exception):
    pass


class _StreamBroke(Exception):
    pass


def as_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_unset=True, warnings=False)
    return obj


def web_tools(config: AgentConfig) -> list[dict]:
    if not config.web_search:
        return []
    tool: dict = {"type": "web_search", "search_context_size": config.search_context_size}
    if config.web_allowed_domains:
        tool["filters"] = {"allowed_domains": list(config.web_allowed_domains)}
    return [tool]


def describe_web_action(action: dict | None) -> tuple[str, str]:
    """(kind, detail) for a web_search_call action, as v2's _describe_search."""
    action = action or {}
    kind = action.get("type") or "search"
    if kind == "search":
        queries = action.get("queries") or ([action["query"]] if action.get("query") else [])
        return "search", ", ".join(repr(q) for q in queries)
    if kind == "open_page":
        return "open_page", action.get("url") or ""
    if kind == "find_in_page":
        return "find_in_page", f"{action.get('pattern')!r} in {action.get('url')}"
    return kind, ""


def output_text(items: Iterable[dict]) -> str:
    return "".join(part.get("text", "") for item in items if item.get("type") == "message"
                   for part in item.get("content") or [] if part.get("type") == "output_text")


def cited_sources(items: Iterable[dict]) -> list[dict]:
    found: list[dict] = []
    for item in items:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            for ann in part.get("annotations") or []:
                if ann.get("type") == "url_citation":
                    src = {"title": ann.get("title") or "", "url": ann.get("url") or ""}
                    if src not in found:
                        found.append(src)
    return found


def all_sources(items: Iterable[dict]) -> list[dict]:
    found: list[dict] = []
    for item in items:
        if item.get("type") == "web_search_call":
            for src in (item.get("action") or {}).get("sources") or []:
                entry = {"url": src.get("url") or "", **({"title": src["title"]} if src.get("title") else {})}
                if entry["url"] and entry not in found:
                    found.append(entry)
    return found


@dataclass
class ModelResponse:
    output: list[dict]                     # items to append to the next request's input
    text: str
    usage: Usage
    cost_usd: float | None
    duration_s: float
    status: str = "completed"
    incomplete_reason: str | None = None
    web: Counter = field(default_factory=Counter)   # search / open_page / find_in_page, incl. retried attempts

    @property
    def function_calls(self) -> list[dict]:
        return [i for i in self.output if i.get("type") == "function_call"]

    @property
    def sources(self) -> list[dict]:
        return cited_sources(self.output)

    @property
    def sources_all(self) -> list[dict]:
        return all_sources(self.output)


class ModelAdapter:
    def __init__(self, config: AgentConfig, client: Any = None, *,
                 retry_delays: tuple[float, ...] = (2.0, 4.0), jitter: float = 1.0):
        self.config = config
        self._client = client
        self.retry_delays = retry_delays
        self.jitter = jitter
        self.dropped_params: set[str] = set()   # optional params/values the API rejected this session
        self._dropped_include: set[str] = set()
        self._unknown_price_noticed = False

    @property
    def client(self):
        if self._client is None:
            self._client = openai.OpenAI(max_retries=3, timeout=request_timeout(self.config.reasoning))
        return self._client

    # -- request -------------------------------------------------------------------------------

    def build_params(self, input_items: list, tools: list[dict], tool_choice: str,
                     cache_key: str | None) -> dict:
        cfg = self.config
        params: dict = {"model": cfg.model, "input": input_items, "tools": tools, "tool_choice": tool_choice,
                        "parallel_tool_calls": True, "reasoning": {"effort": cfg.reasoning}, "store": cfg.store}
        include = [*(["reasoning.encrypted_content"] if not cfg.store else []),
                   *(["web_search_call.action.sources"] if cfg.web_search else [])]
        include = [v for v in include if v not in self._dropped_include]
        if include and "include" not in self.dropped_params:
            params["include"] = include
        if cache_key and "prompt_cache_key" not in self.dropped_params:
            params["prompt_cache_key"] = cache_key
        return params

    def _open_stream(self, params: dict) -> Iterable[Any]:
        """Start the streamed request. Overridden by the test fake."""
        return self.client.responses.create(**params, stream=True)

    def _drop_rejected(self, err: openai.BadRequestError, params: dict, emit: Emit) -> bool:
        """If the 400 names an optional param (or include value), drop it for the session and say so."""
        text = f"{getattr(err, 'param', '') or ''} {getattr(err, 'message', '') or err}"
        if "include" in params:
            named = [v for v in params["include"] if v in text]
            if named or "include" in text:
                values = named or list(params["include"])
                self._dropped_include.update(values)
                emit(Notice(level="warning", code="include_rejected",
                            message=f"The API rejected include={values}; continuing without it."))
                return True
        if "prompt_cache_key" in params and "prompt_cache_key" in text:
            self.dropped_params.add("prompt_cache_key")
            emit(Notice(level="warning", code="prompt_cache_key_rejected",
                        message="The API rejected prompt_cache_key; continuing without it."))
            return True
        return False

    def _start(self, input_items, tools, tool_choice, cache_key, emit: Emit):
        for _ in range(4):
            params = self.build_params(input_items, tools, tool_choice, cache_key)
            try:
                return self._open_stream(params)
            except openai.BadRequestError as e:
                if not self._drop_rejected(e, params, emit):
                    raise ModelError(f"The API rejected the request: {getattr(e, 'message', e)}", "bad_request") from e
            except openai.APIConnectionError as e:
                raise ModelError(f"Could not reach the API: {e}", "connection_error") from e
            except openai.APIError as e:
                raise ModelError(f"{type(e).__name__}: {getattr(e, 'message', e)}", "api_error") from e
        raise ModelError("The API kept rejecting optional request parameters.", "bad_request")

    # -- one round -----------------------------------------------------------------------------

    def respond(self, input_items: list, *, tools: list[dict], round_no: int, cancel: CancelToken,
                emit: Emit, tool_choice: str = "auto", cache_key: str | None = None) -> ModelResponse:
        started = time.monotonic()
        web: Counter = Counter()
        attempt = 0
        while True:
            try:
                final = self._attempt(input_items, tools, tool_choice, cache_key, round_no, cancel, emit, web)
                break
            except _StreamBroke as e:
                if attempt >= len(self.retry_delays):
                    raise ModelError(f"The response stream broke {attempt + 1} times; last error: {e}",
                                     "stream_error") from e
                delay = self.retry_delays[attempt] + random.uniform(0, self.jitter)
                attempt += 1
                emit(ModelRetry(round=round_no, attempt=attempt, reason=str(e)[:200], delay_s=round(delay, 2)))
                if cancel.wait(delay):
                    raise Cancelled() from e
        return self._finish(final, web, time.monotonic() - started, emit)

    def _attempt(self, input_items, tools, tool_choice, cache_key, round_no, cancel: CancelToken,
                 emit: Emit, web: Counter) -> dict:
        if cancel.cancelled:
            raise Cancelled()
        stream = self._start(input_items, tools, tool_choice, cache_key, emit)
        close = getattr(stream, "close", None)
        if close is not None:
            cancel.add_callback(close)     # unblocks a read stuck on the network when the user cancels
        final = None
        try:
            for raw in stream:
                if cancel.cancelled:
                    raise Cancelled()
                ev = as_dict(raw)
                kind = ev.get("type")
                if kind == "response.output_text.delta":
                    emit(TextDelta(round=round_no, text=ev.get("delta") or ""))
                elif kind == "response.output_item.done":
                    item = as_dict(ev.get("item")) or {}
                    if item.get("type") == "web_search_call":
                        wkind, detail = describe_web_action(item.get("action"))
                        web[wkind] += 1
                        emit(WebAction(kind=wkind, detail=detail))
                elif kind in ("response.completed", "response.incomplete"):
                    final = as_dict(ev.get("response"))
                    break
                elif kind == "response.failed":
                    err = (as_dict(ev.get("response")) or {}).get("error") or {}
                    raise ModelError(f"The model response failed: {err.get('message') or err or 'unknown error'}",
                                     err.get("code") or "response_failed")
                elif kind == "error":
                    raise ModelError(f"Stream error: {ev.get('message') or ev}", ev.get("code") or "stream_error")
        except (Cancelled, ModelError):
            raise
        except Exception as e:
            if cancel.cancelled:
                raise Cancelled() from e
            if isinstance(e, RETRYABLE_STREAM_ERRORS):
                raise _StreamBroke(f"{type(e).__name__}: {e}") from e
            if isinstance(e, openai.APIError):
                raise ModelError(f"{type(e).__name__}: {getattr(e, 'message', e)}", "api_error") from e
            raise
        finally:
            if close is not None:
                cancel.remove_callback(close)
                try:
                    close()
                except Exception:
                    pass
        if cancel.cancelled:
            raise Cancelled()
        if final is None:
            raise _StreamBroke("stream ended before response.completed")
        return final

    def _finish(self, final: dict, web: Counter, duration: float, emit: Emit) -> ModelResponse:
        output = [as_dict(i) for i in final.get("output") or []]
        usage = Usage.from_api(final.get("usage"))
        cost = cost_usd(self.config.model, usage)
        if cost is None and not self._unknown_price_noticed:
            self._unknown_price_noticed = True
            emit(Notice(level="warning", code="unknown_pricing",
                        message=f"No price table entry for model '{self.config.model}'; cost is not tracked."))
        status = final.get("status") or "completed"
        reason = None
        if status == "incomplete":
            reason = (final.get("incomplete_details") or {}).get("reason") or "unknown"
            emit(Notice(level="warning", code="response_incomplete",
                        message=f"The model's response was cut short ({reason}). Continuing with what it returned."))
        return ModelResponse(output=output, text=output_text(output), usage=usage, cost_usd=cost,
                             duration_s=round(duration, 3), status=status, incomplete_reason=reason, web=web)
