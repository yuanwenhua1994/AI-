"""Small standard-library adapters for luwx. No Stata dependency.

chat() accepts OpenAI-style text messages and function tools. Native response
metadata in ``_provider`` must be retained in history for subsequent tool turns.
This module sends no requests at import time and never prints credentials.
"""
from __future__ import annotations

import copy
import ipaddress
import json
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ProviderError(RuntimeError):
    """An actionable API or transport error, with credentials redacted."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def redact(text, config=None):
    text = str(text)
    key = str((config or {}).get("api_key") or "")
    if key:
        for secret in (key, urllib.parse.quote(key, safe="")):
            text = text.replace(secret, "[密钥已隐藏]")
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "[密钥已隐藏]", text)
    text = re.sub(r"(?i)(bearer\s+)[^\s\"<>]+", r"\1[密钥已隐藏]", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", text)
    return text


def _bool(value):
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off", ""):
            return False
        raise ValueError("allowhttp 必须为 true 或 false。")
    return bool(value)


def validate_config(config):
    """Validate and return a copy; accept every nonempty API-key format."""
    result = dict(config)
    result["protocol"] = str(result.get("protocol") or "openai").lower()
    if result["protocol"] not in ("openai", "anthropic", "gemini"):
        raise ValueError("protocol() 请选择 openai、anthropic 或 gemini。")
    result["auth"] = str(result.get("auth") or "bearer").lower()
    if result["auth"] not in ("bearer", "none"):
        raise ValueError("auth() 请选择 bearer 或 none。")
    result["api_key"] = str(result.get("api_key") or "").strip()
    if result["auth"] != "none" and not result["api_key"]:
        raise ValueError("尚未配置密钥。请用 keyfile() 或环境变量配置；本地免密钥服务可用 auth(none)。")
    if any(c in result["api_key"] for c in "\r\n"):
        raise ValueError("密钥包含换行，请仅保存密钥本身。")
    result["model"] = str(result.get("model") or "").strip()
    if not result["model"] or any(c in result["model"] for c in "\r\n"):
        raise ValueError("请填写平台提供的准确 model() 名称。")
    result["base_url"] = str(result.get("base_url") or "").strip().rstrip("/")
    result["allowhttp"] = _bool(result.get("allowhttp", False))
    try:
        parsed = urllib.parse.urlsplit(result["base_url"])
        parsed.port
    except ValueError:
        raise ValueError("baseurl() 不是有效的 API 地址。") from None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("baseurl() 需要完整的 https:// 地址或本地 http:// 地址。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("baseurl() 不应包含账号、密钥、查询参数或 # 片段；密钥请另行配置。")
    if any(c.isspace() for c in result["base_url"]):
        raise ValueError("baseurl() 含有空格或换行。")
    local = parsed.hostname.lower() == "localhost" or parsed.hostname.lower().endswith(".localhost")
    try:
        local = local or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        pass
    if parsed.scheme == "http" and not local and not result["allowhttp"]:
        raise ValueError("远程 API 请使用 HTTPS。本地 localhost 可用 HTTP；确认内网服务后可显式设置 allowhttp。")
    for name, default, low, high in (("timeout", 180, 1, 600), ("max_output_tokens", 4096, 1, 65536)):
        try:
            val = int(result.get(name, default))
        except (TypeError, ValueError):
            raise ValueError(name + " 必须为整数。") from None
        if not low <= val <= high:
            raise ValueError(name + " 超出允许范围。")
        result[name] = val
    result["effort"] = str(result.get("effort") or "default").lower()
    if result["effort"] not in ("default", "low", "medium", "high", "max"):
        raise ValueError("effort() 请选择 default、low、medium、high 或 max。")
    if result["protocol"] == "gemini" and result["effort"] == "max":
        raise ValueError("Gemini 原生 thinkingLevel 没有 max；请选择 default、low、medium 或 high。")
    return result


def endpoint(config):
    """Construct the provider endpoint without requiring a key."""
    base = str(config.get("base_url") or "").rstrip("/")
    protocol = str(config.get("protocol") or "openai").lower()
    path = urllib.parse.urlsplit(base).path.rstrip("/")
    if protocol == "openai":
        if path.endswith("/chat/completions"):
            return base
        if path.endswith("/responses") or path.endswith("/messages"):
            raise ValueError("OpenAI 协议需要 Chat Completions 地址；不支持 Responses 或 Messages 地址。")
        return base + ("/v1" if not path else "") + "/chat/completions"
    if protocol == "anthropic":
        if path.endswith("/messages"):
            return base
        return base + ("" if path.endswith("/v1") else "/v1") + "/messages"
    if protocol == "gemini":
        model = str(config.get("model") or "").removeprefix("models/")
        if path.endswith(":generateContent"):
            actual = urllib.parse.unquote(path.rsplit("/models/", 1)[-1].removesuffix(":generateContent"))
            if actual != model:
                raise ValueError("Gemini 完整请求地址中的模型与 model() 不一致。")
            return base
        prefix = base if path else base + "/v1beta"
        return prefix + "/models/" + urllib.parse.quote(model, safe="") + ":generateContent"
    raise ValueError("不支持的 API 协议。")


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(p.get("text", "")) for p in value if isinstance(p, dict) and not p.get("thought"))
    raise ValueError("目前仅支持文本消息，不支持图片、音频或文件内容。")


def _arguments(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("模型返回的工具参数不是有效 JSON。") from None
    if not isinstance(value, dict):
        raise ValueError("工具参数必须为 JSON 对象。")
    return value


def _function_tools(tools):
    output = []
    for tool in tools or []:
        if tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
            raise ValueError("目前只支持 function 类型的工具。")
        fn = tool["function"]
        if not fn.get("name"):
            raise ValueError("工具缺少 name。")
        output.append(fn)
    return output


def _append_native(messages, role, parts):
    if not parts:
        return
    if messages and messages[-1]["role"] == role:
        messages[-1]["content" if "content" in messages[-1] else "parts"].extend(parts)
    else:
        messages.append({"role": role, "content": parts})


def _anthropic_messages(messages):
    system, converted = [], []
    for msg in messages:
        role = msg.get("role")
        if role in ("system", "developer"):
            system.append(_text(msg.get("content")))
        elif role == "tool":
            if not msg.get("tool_call_id"):
                raise ValueError("工具结果缺少 tool_call_id。")
            block = {"type": "tool_result", "tool_use_id": msg["tool_call_id"], "content": _text(msg.get("content"))}
            if msg.get("is_error"):
                block["is_error"] = True
            _append_native(converted, "user", [block])
        elif role in ("user", "assistant"):
            raw = msg.get("_provider", {})
            if role == "assistant" and raw.get("protocol") == "anthropic":
                blocks = copy.deepcopy(raw["content"])
            else:
                text = _text(msg.get("content"))
                blocks = [{"type": "text", "text": text}] if text else []
                for call in msg.get("tool_calls", []):
                    fn = call["function"]
                    blocks.append({"type": "tool_use", "id": call["id"], "name": fn["name"], "input": _arguments(fn.get("arguments", {}))})
            _append_native(converted, role, blocks)
        else:
            raise ValueError("不支持的消息角色。")
    return "\n\n".join(system), converted


def _gemini_messages(messages):
    system, converted, calls = [], [], {}
    for msg in messages:
        for call in msg.get("tool_calls", []):
            calls[call["id"]] = call["function"]["name"]
        role = msg.get("role")
        if role in ("system", "developer"):
            system.append(_text(msg.get("content")))
            continue
        if role == "tool":
            ident = msg.get("tool_call_id")
            name = msg.get("name") or calls.get(ident)
            if not name:
                raise ValueError("工具结果无法对应原来的函数名。")
            text = _text(msg.get("content"))
            try:
                result = json.loads(text)
            except ValueError:
                result = {"output": text}
            if not isinstance(result, dict):
                result = {"output": result}
            response = {"name": name, "response": result}
            # Synthetic IDs are internal only; old Gemini models omit IDs.
            if ident and not ident.startswith("gemini_local_"):
                response["id"] = ident
            native_role, parts = "user", [{"functionResponse": response}]
        elif role in ("user", "assistant"):
            native_role = "model" if role == "assistant" else "user"
            raw = msg.get("_provider", {})
            if role == "assistant" and raw.get("protocol") == "gemini":
                parts = copy.deepcopy(raw["parts"])
            else:
                text = _text(msg.get("content"))
                parts = [{"text": text}] if text else []
                for call in msg.get("tool_calls", []):
                    fn = call["function"]
                    fc = {"name": fn["name"], "args": _arguments(fn.get("arguments", {}))}
                    if not call["id"].startswith("gemini_local_"):
                        fc["id"] = call["id"]
                    parts.append({"functionCall": fc})
        else:
            raise ValueError("不支持的消息角色。")
        if not parts:
            continue
        if converted and converted[-1]["role"] == native_role:
            converted[-1]["parts"].extend(parts)
        else:
            converted.append({"role": native_role, "parts": parts})
    return "\n\n".join(system), converted


def build_request(config, messages, tools=None):
    """Return (validated config, Request). Useful for reproducible tests."""
    cfg = validate_config(config)
    if not isinstance(messages, list) or not messages:
        raise ValueError("至少需要一条消息。")
    protocol = cfg["protocol"]
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "luwx/3.0"}
    functions = _function_tools(tools)
    if protocol == "openai":
        clean = []
        for msg in messages:
            item = {k: copy.deepcopy(v) for k, v in msg.items() if k in ("role", "content", "name", "tool_calls", "tool_call_id")}
            native = msg.get("_provider", {})
            if msg.get("role") == "assistant" and native.get("protocol") == "openai" and "reasoning_content" in native:
                # DeepSeek and some compatible thinking models require this
                # opaque provider field in all turns of a tool conversation.
                item["reasoning_content"] = copy.deepcopy(native["reasoning_content"])
            clean.append(item)
        body = {"model": cfg["model"], "messages": clean, "stream": False}
        if functions:
            body.update(tools=copy.deepcopy(tools), tool_choice="auto")
        if cfg["effort"] != "default":
            body["reasoning_effort"] = cfg["effort"]
        if config.get("max_output_tokens") is not None:
            body["max_completion_tokens"] = cfg["max_output_tokens"]
        if cfg["auth"] != "none":
            headers["Authorization"] = "Bearer " + cfg["api_key"]
    elif protocol == "anthropic":
        system, native = _anthropic_messages(messages)
        body = {"model": cfg["model"], "messages": native, "max_tokens": cfg["max_output_tokens"], "stream": False}
        if system:
            body["system"] = system
        if functions:
            body["tools"] = [{"name": fn["name"], "description": fn.get("description", ""), "input_schema": copy.deepcopy(fn.get("parameters", {"type": "object", "properties": {}}))} for fn in functions]
            body["tool_choice"] = {"type": "auto"}
        if cfg["effort"] != "default":
            body["output_config"] = {"effort": cfg["effort"]}
        headers["anthropic-version"] = "2023-06-01"
        if cfg["auth"] != "none":
            headers["x-api-key"] = cfg["api_key"]
    else:
        system, native = _gemini_messages(messages)
        body = {"contents": native, "generationConfig": {"maxOutputTokens": cfg["max_output_tokens"]}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if functions:
            body["tools"] = [{"functionDeclarations": [{"name": fn["name"], "description": fn.get("description", ""), "parametersJsonSchema": copy.deepcopy(fn.get("parameters", {"type": "object", "properties": {}}))} for fn in functions]}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        if cfg["effort"] != "default":
            body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": cfg["effort"].upper()}
        if cfg["auth"] != "none":
            headers["x-goog-api-key"] = cfg["api_key"]
    data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return cfg, urllib.request.Request(endpoint(cfg), data=data, headers=headers, method="POST")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Prevent credentials from being forwarded to a different host or HTTP.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _error_text(data):
    if isinstance(data, dict):
        error = data.get("error", data)
        if isinstance(error, dict):
            return str(error.get("message") or error.get("type") or "服务端未提供错误详情")
        return str(error)
    return str(data)


def _http_hint(status):
    return {400: "核对协议、模型、工具和 effort 参数。", 401: "检查密钥是否有效及平台是否对应。", 403: "检查密钥权限、模型访问权限或网络限制。", 404: "检查 baseurl() 和 model()，以及平台是否支持此协议。", 429: "额度或请求频率受限；稍后重试或查看平台额度。"}.get(status, "请查看平台状态；必要时稍后重试。")


def _normalize(data, protocol):
    if not isinstance(data, dict):
        raise ProviderError("API 返回的 JSON 不是对象。")
    if data.get("error"):
        raise ProviderError("API 返回错误：" + _error_text(data))
    output = {"role": "assistant", "content": ""}
    calls = []
    if protocol == "openai":
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("回复中没有 choices[0].message。请选择正确的 OpenAI Chat Completions 协议。") from None
        output["content"] = _text(message.get("content")) or _text(message.get("refusal"))
        if "reasoning_content" in message:
            output["_provider"] = {"protocol": "openai", "reasoning_content": copy.deepcopy(message["reasoning_content"])}
        for call in message.get("tool_calls") or []:
            if call.get("type", "function") != "function":
                raise ProviderError("平台返回了不支持的工具类型。")
            fn = call["function"]
            arguments = fn.get("arguments", "{}")
            calls.append({"id": call.get("id") or "call_" + uuid.uuid4().hex, "type": "function", "function": {"name": fn["name"], "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)}})
    elif protocol == "anthropic":
        blocks = data.get("content")
        if not isinstance(blocks, list):
            raise ProviderError("回复中没有 Anthropic content 数组。请核对 protocol()。")
        output["content"] = "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        output["_provider"] = {"protocol": "anthropic", "content": copy.deepcopy(blocks)}
        for block in blocks:
            if block.get("type") == "tool_use":
                calls.append({"id": block["id"], "type": "function", "function": {"name": block["name"], "arguments": json.dumps(block.get("input", {}), ensure_ascii=False)}})
    else:
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError):
            feedback = data.get("promptFeedback", {}).get("blockReason", "")
            raise ProviderError("回复中没有 Gemini candidates 内容。" + ("平台拦截原因：" + str(feedback) if feedback else "请核对协议、模型或安全过滤状态。")) from None
        output["content"] = "\n".join(part.get("text", "") for part in parts if not part.get("thought"))
        output["_provider"] = {"protocol": "gemini", "parts": copy.deepcopy(parts)}
        for part in parts:
            fn = part.get("functionCall")
            if fn:
                calls.append({"id": fn.get("id") or "gemini_local_" + uuid.uuid4().hex, "type": "function", "function": {"name": fn["name"], "arguments": json.dumps(fn.get("args", {}), ensure_ascii=False)}})
    if calls:
        output["tool_calls"] = calls
    if not output["content"] and not calls:
        raise ProviderError("平台返回空回复。可能达到输出上限或被过滤；请检查平台响应设置。")
    return output


def chat(config, messages, tools=None):
    """Send one non-streaming request. Does not execute any returned tool."""
    try:
        cfg, request = build_request(config, messages, tools)
        opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(request, timeout=cfg["timeout"]) as response:
                raw = response.read(20 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raw_error = error.read(16384).decode("utf-8", "replace")
            try:
                detail = _error_text(json.loads(raw_error))
            except ValueError:
                # A partial/HTML error could contain a truncated or escaped key.
                # Do not display arbitrary raw pages in students' Stata logs.
                detail = "服务器未返回完整的 JSON 错误详情。"
            if 300 <= error.code < 400:
                detail = "服务器要求跳转。为保护密钥，未跟随跳转；请配置最终 API 地址。"
            raise ProviderError("API HTTP " + str(error.code) + "：" + redact(detail, cfg)[:1000] + " " + _http_hint(error.code), error.code) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
            reason = getattr(error, "reason", error)
            raise ProviderError("无法连接 API：" + redact(reason, cfg)[:700] + "。请检查网络、代理、证书和 timeout()；TLS 证书验证保持开启。") from None
        if len(raw) > 20 * 1024 * 1024:
            raise ProviderError("API 返回内容过大，超过 20 MB。")
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeError, ValueError):
            # Do not echo arbitrary HTML/pages or an unexpected response.
            raise ProviderError("API 没有返回有效 JSON。请核对 API 地址，避免填成网页地址。") from None
        return _normalize(data, cfg["protocol"])
    except ProviderError as error:
        raise ProviderError(redact(str(error), config), error.status) from None
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderError("API 配置或数据格式错误：" + redact(error, config)) from None
