from __future__ import annotations

import os
import json
import asyncio
import time
from typing import Optional, Any

import re
from .logger import get_logger
from .agentic_apps_api import agentic_apps_api, Provider
from .phoenix import create_llm_span, set_llm_output
import boto3


from crewai.llms.base_llm import BaseLLM as _CrewAIBase
from openai import AsyncAzureOpenAI, AzureOpenAI


class CrewAILLM(_CrewAIBase):
    """Wrapper around `LLM` providing CrewAI-compatible `call()` and
    response text extraction.

    This class lives in the SDK so it can be reused by different backends
    while keeping the LLM response parsing encapsulated here.
    """

    def __init__(self, llm: 'LLM', model: str = "custom", **kwargs: Any):
        # If CrewAI BaseLLM expects parameters, try to initialize it.
        try:
            super().__init__(model=model, provider="custom", **kwargs)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._llm = llm
        self._initialized = False

    async def init(self) -> None:
        if not self._initialized:
            await self._llm.init()
            self._initialized = True

    def call(self, messages: str | list[dict[str, Any]], *args, **kwargs) -> str | Any:
        # Convert messages to prompt
        if isinstance(messages, str):
            prompt = messages
        else:
            prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt += f"{role}: {content}\n"

        # Ensure init (synchronously)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.init())
        except RuntimeError:
            pass

        resp = self._llm.generate_sync(prompt)
        return self._extract_text_from_response(resp)

    async def generate(self, prompt: str) -> Any:
        await self.init()
        return await self._llm.generate(prompt)

    def _extract_text_from_response(self, resp: Any) -> str:
        # Bedrock response dict
        if isinstance(resp, dict):
            try:
                output = resp.get("output") or {}
                message = output.get("message") or {}
                content = message.get("content") or []
                if content and isinstance(content, list):
                    text = content[0].get("text")
                    if text:
                        text = str(text)
                        if text.startswith("```"):
                            # remove fences and optional json header
                            parts = text.split("```", 2)
                            if len(parts) >= 2:
                                inner = parts[1]
                                inner = inner.lstrip("json\n")
                                return inner.strip()
                        return text.strip()
            except Exception:
                pass
            try:
                return json.dumps(resp)
            except Exception:
                return str(resp)

        # OpenAI ChatCompletion-like objects (openai.AzureOpenAI chat/completions)
        try:
            choices = getattr(resp, "choices", None)
            if choices and len(choices) > 0:
                first = choices[0]
                # choice.message.content
                msg = getattr(first, "message", None)
                if msg is not None:
                    # content may be a simple string
                    content = getattr(msg, "content", None)
                    if isinstance(content, str) and content:
                        return content.strip()
                    # or content may be an object with .content or .text
                    if isinstance(content, dict):
                        # try common keys
                        for k in ("content", "text", "message", "body"):
                            if k in content and isinstance(content[k], str):
                                return content[k].strip()
                    # some SDKs expose message.content as an object with .content attribute
                    if hasattr(content, "content"):
                        inner = getattr(content, "content")
                        if isinstance(inner, str):
                            return inner.strip()

                # fallback: some Choice objects expose .text or .content directly
                text = getattr(first, "text", None) or getattr(first, "content", None)
                if isinstance(text, str) and text:
                    return text.strip()
        except Exception:
            pass
        # OpenAI Responses API objects may expose output_text or nested content
        try:
            output_text = getattr(resp, "output_text", None)
            if output_text:
                return str(output_text)
        except Exception:
            pass
        try:
            output = getattr(resp, "output", None)
            if output and isinstance(output, list):
                content = getattr(output[0], "content", None)
                if content and isinstance(content, list):
                    text = getattr(content[0], "text", None)
                    if text:
                        return str(text)
        except Exception:
            pass

        return str(resp)



class BaseAdapter:
    def __init__(self, model_id: str, model_name: str, provider_cfg: dict, logger):
        self.model_id = model_id
        self.model_name = model_name
        self.provider_cfg = provider_cfg or {}
        self._logger = logger

    async def init(self) -> None:
        return None

    def generate_sync(self, payload: dict) -> Any:
        raise NotImplementedError()

    async def generate(self, payload: dict) -> Any:
        return await asyncio.to_thread(self.generate_sync, payload)


class BedrockAdapter(BaseAdapter):
    def __init__(self, model_id: str, model_name: str, provider_cfg: dict, logger):
        super().__init__(model_id, model_name, provider_cfg, logger)
        self._client = None

    async def init(self, region: str | None = None) -> None:
        # Prepare boto3 client with provided credentials and region
        region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        try:
            session = boto3.session.Session(
                aws_access_key_id=self.provider_cfg.get("accessKeyId"),
                aws_secret_access_key=self.provider_cfg.get("secretAccessKey"),
                aws_session_token=self.provider_cfg.get("sessionToken"),
            )
            try:
                self._client = session.client("bedrock-runtime", region_name=region)
            except Exception:
                self._client = session.client("bedrock", region_name=region)
            self._logger.debug("Initialized Bedrock client: %s (region=%s)", type(self._client), region)
        except Exception as exc:
            self._logger.error("Failed to init Bedrock client: %s", exc)
            raise

    def generate_sync(self, payload: dict) -> Any:
        if self._client is None:
            raise RuntimeError("Bedrock client not initialized")
        converse_kwargs = {"modelId": self.model_id, **(payload or {})}

        start = time.time()
        try:
            resp = self._client.converse(**converse_kwargs)
            duration = time.time() - start

            try:
                resp_str = str(resp)
            except Exception:
                resp_str = "<unserializable response>"

            self._logger.info(f"{duration:.2f}s: BedrockAdapter.converse(), request={converse_kwargs}, response={resp_str}")
            return resp
        except Exception as exc:
            duration = time.time() - start
            self._logger.error(f"{duration:.2f}s: BedrockAdapter.converse() FAILED, request={converse_kwargs}, error={exc}")
            raise


class AzureAdapter(BaseAdapter):
    def __init__(self, model_id: str, model_name: str, provider_cfg: dict, logger):
        super().__init__(model_id, model_name, provider_cfg, logger)
        # Support multiple naming conventions for API key and endpoint
        self.api_key = (
            provider_cfg.get("apiKey") or
            provider_cfg.get("azureOpenAiApiKey") or
            provider_cfg.get("azure_openai_api_key")
        )
        self.api_base = (
            provider_cfg.get("apiBaseUrl") or
            provider_cfg.get("azureOpenAiEndpoint") or
            provider_cfg.get("azure_openai_endpoint")
        )
        self._client = None
        self._async_client = None
        self._api_version = (
            provider_cfg.get("apiVersion") or
            provider_cfg.get("api_version") or
            provider_cfg.get("azureOpenAiApiVersion") or
            provider_cfg.get("azure_openai_api_version") or
            "2023-07-01-preview"
        )

    async def init(self) -> None:
        if not (self.api_key and self.api_base):
            raise RuntimeError("Azure API key or base URL missing in provider config")
        # Initialize Azure OpenAI client using the `openai.AzureOpenAI` wrapper
        self._client = AzureOpenAI(api_version=self._api_version, api_key=self.api_key, azure_endpoint=self.api_base)
        self._async_client = AsyncAzureOpenAI(
            api_version=self._api_version,
            api_key=self.api_key,
            azure_endpoint=self.api_base,
        )
        self._logger.debug("Initialized Azure AzureOpenAI client (base=%s, api_version=%s)", self.api_base, self._api_version)

    def _build_api_params(self, payload: dict) -> dict:
        model_id = self.model_id
        # convert our payload messages into simple chat inputs
        messages = []
        for m in payload.get("messages", []):
            role = m.get("role", "user")
            parts = m.get("content") or []
            text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)])
            messages.append({"role": role, "content": text})

        # Convert Bedrock tool format to Azure OpenAI function format
        tools = None
        tool_choice = None
        bedrock_tools = payload.get("toolConfig", {}).get("tools", [])
        
        if bedrock_tools:
            tools = []
            for bedrock_tool in bedrock_tools:
                tool_spec = bedrock_tool.get("toolSpec", {})
                
                # Extract inputSchema - handle both direct schema and wrapped {"json": schema} format
                input_schema = tool_spec.get("inputSchema", {})
                if isinstance(input_schema, dict) and "json" in input_schema:
                    # Unwrap the schema from {"json": {...}} format
                    input_schema = input_schema.get("json", {})
                
                # Ensure the schema has a valid type field
                if not input_schema or not isinstance(input_schema, dict):
                    input_schema = {"type": "object", "properties": {}}
                elif "type" not in input_schema:
                    input_schema["type"] = "object"
                
                # Convert Bedrock toolSpec to Azure OpenAI function format
                azure_function = {
                    "type": "function",
                    "function": {
                        "name": tool_spec.get("name", ""),
                        "description": tool_spec.get("description", ""),
                        "parameters": input_schema
                    }
                }
                tools.append(azure_function)
            
            # Handle tool_choice parameter
            bedrock_tool_choice = payload.get("toolConfig", {}).get("toolChoice")
            if bedrock_tool_choice:
                if isinstance(bedrock_tool_choice, dict):
                    choice_type = bedrock_tool_choice.get("type")
                    if choice_type == "auto":
                        tool_choice = "auto"
                    elif choice_type == "any":
                        tool_choice = "required"
                    elif choice_type == "tool":
                        # Specific tool choice
                        tool_name = bedrock_tool_choice.get("name")
                        if tool_name:
                            tool_choice = {"type": "function", "function": {"name": tool_name}}
                else:
                    tool_choice = "auto"
            else:
                tool_choice = "auto"
            
            self._logger.debug(f"Converted {len(tools)} Bedrock tools to Azure OpenAI format")

        # Build API parameters
        api_params = {
            "model": model_id,
            "messages": messages
        }
        
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = tool_choice
            self._logger.debug(f"Azure OpenAI call with {len(tools)} tools, tool_choice={tool_choice}")

        return api_params

    def generate_sync(self, payload: dict) -> Any:
        if self._client is None:
            raise RuntimeError("Azure client not initialized; call init() first")
        api_params = self._build_api_params(payload)
        messages = api_params["messages"]
        tool_count = len(api_params.get("tools") or [])

        start = time.time()
        try:
            resp = self._client.chat.completions.create(**api_params)
            duration = time.time() - start
            try:
                resp_str = str(resp)
            except Exception:
                resp_str = "<unserializable response>"
            self._logger.info(f"{duration:.2f}s: AzureAdapter.chat.completions.create(), request={messages}, tools={tool_count}, response={resp_str}")
            return resp
        except Exception as exc:
            duration = round(time.time() - start, 3)
            self._logger.error(f"{duration:.2f}s: AzureAdapter.chat.completions.create() FAILED, request={messages}, error={exc}")
            raise

    async def generate(self, payload: dict) -> Any:
        if self._async_client is None:
            raise RuntimeError("Azure async client not initialized; call init() first")
        api_params = self._build_api_params(payload)
        messages = api_params["messages"]
        tool_count = len(api_params.get("tools") or [])

        start = time.time()
        try:
            resp = await self._async_client.chat.completions.create(**api_params)
            duration = time.time() - start
            try:
                resp_str = str(resp)
            except Exception:
                resp_str = "<unserializable response>"
            self._logger.info(f"{duration:.2f}s: AzureAdapter.chat.completions.create(), request={messages}, tools={tool_count}, response={resp_str}")
            return resp
        except Exception as exc:
            duration = round(time.time() - start, 3)
            self._logger.error(f"{duration:.2f}s: AzureAdapter.chat.completions.create() FAILED, request={messages}, error={exc}")
            raise


class LLM:
    """LLM wrapper that discovers model info via ICA and invokes Bedrock.

    Constructor parameters:
      - provider: 'aws' | 'azure'
      - model: model name (search substring, e.g. 'claude-sonnet')

    After `init()` is called, the instance will have credentials and
    `model_id` populated and will be able to call `generate()`.
    """

    # Shared cache across all LLM instances to avoid repeated ICA fetches
    _config_json: Optional[dict] = None

    def __init__(self, provider: Provider, model: str):
        try:
              self.provider = Provider(provider)
        except Exception:
            raise ValueError(f"Unsupported provider: {provider}")
        self.model = model

        self.account_id: Optional[str] = None
        self.access_key_id: Optional[str] = None
        self.secret_access_key: Optional[str] = None
        self.model_id: Optional[str] = None
        self.model_name: Optional[str] = None

        self._logger = get_logger(__name__)
        self._client = None
        self.adapter: BaseAdapter | None = None
        # Azure-specific
        self.azure_api_key: Optional[str] = None
        self.azure_api_base: Optional[str] = None

    async def init(self) -> None:
        # Use shared class cache when available
        if type(self)._config_json is not None:
            data = type(self)._config_json
        else:
            data = await self._fetch_ica_config()
            type(self)._config_json = data

        provider_entry = self._find_provider_entry(data)
        if provider_entry is None:
            raise RuntimeError(f"Provider '{self.provider.value}' not found in ICA provider configs")

        provider_cfg = provider_entry.get("providerConfig") or {}

        # Choose adapter based on provider and prepare credentials
        if self.provider == Provider.azure:
            self.adapter = AzureAdapter(None, None, provider_cfg, self._logger)
        else:
            self.adapter = BedrockAdapter(None, None, provider_cfg, self._logger)

        model_entry = self._find_model_entry(provider_entry)
        if model_entry is None:
            raise RuntimeError(f"Model matching '{self.model}' not found for provider '{self.provider.value}'")

        self.model_id = model_entry.get("modelId") or model_entry.get("model_id")
        self.model_name = model_entry.get("modelName") or model_entry.get("model_name")

        # update adapter with model identifiers and initialize it
        if self.adapter is None:
            raise RuntimeError("Failed to create adapter for provider")
        self.adapter.model_id = self.model_id
        self.adapter.model_name = self.model_name
        if isinstance(self.adapter, BedrockAdapter):
            region = self._infer_region(self.model_id)
            await self.adapter.init(region)
        else:
            await self.adapter.init()

    async def _fetch_ica_config(self) -> dict:
        """Fetch ICA provider configuration using the common agentic_apps_api."""
        self._logger.info("Fetching ICA provider config using agentic_apps_api")
        try:
            data = await agentic_apps_api.get_provider_settings()
            # Log a concise summary of providers and their models
            providers = data.get("providers") or []
            lines = []
            for p in providers:
                pname = p.get("provider") or p.get("providerName") or "unknown"
                lines.append(f"{pname}:")
                for m in (p.get("models") or []):
                    mid = m.get("modelId") or m.get("modelName") or m.get("model_id") or m.get("model_name") or "<unknown>"
                    lines.append(f"  {mid}")
            if lines:
                summary = "\n".join(lines)
                self._logger.info("ICA providers/models:\n%s", summary)
            return data
        except Exception as exc:
            self._logger.error("Failed to fetch ICA provider config: %s", exc)
            raise

    def _find_provider_entry(self, data: dict) -> dict | None:
        """Find provider entry, treating 'azure' as an alias for 'ica' provider."""
        provider_value = str(self.provider.value)

        # First try exact match
        result = next((p for p in (data.get("providers") or []) if str(p.get("provider")) == provider_value), None)

        # If not found and looking for 'azure', try 'ica' as fallback
        if result is None and provider_value == "azure":
            result = next((p for p in (data.get("providers") or []) if str(p.get("provider")) == "ica"), None)
            if result:
                self._logger.info("Provider 'azure' not found, using 'ica' provider as fallback")

        return result

    def _find_model_entry(self, provider_entry: dict) -> dict | None:
        return next((m for m in (provider_entry.get("models") or []) if (m.get("modelId") or "").find(self.model) != -1), None)

    def _infer_region(self, model_id: str) -> str:
        m = re.match(r"arn:aws:bedrock:([^:]+):", str(model_id or ""))
        return m.group(1) if m else os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    def _llm_span_name(self) -> str:
        if isinstance(self.adapter, AzureAdapter):
            return "azure.chat.completions.create"
        if isinstance(self.adapter, BedrockAdapter):
            return "aws.bedrock.converse"
        return "llm.generate"

    def _trace_input_value(self, prompt: str | list[dict[str, Any]]) -> str:
        if isinstance(prompt, str):
            return prompt
        return json.dumps(self._trace_input_messages(prompt), ensure_ascii=False)

    def _trace_input_messages(self, prompt: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]

        messages: list[dict[str, Any]] = []
        for message in prompt:
            role = str(message.get("role") or "user").lower()
            if role not in {"user", "assistant"}:
                role = "user"

            content = message.get("content", "")
            if isinstance(content, list):
                text = "\n".join(
                    str(part.get("text") or "")
                    for part in content
                    if isinstance(part, dict) and "text" in part
                )
                content = text if text else str(content)

            messages.append({"role": role, "content": str(content)})

        return messages or [{"role": "user", "content": ""}]

    def _trace_invocation_parameters(self, payload: dict) -> dict[str, Any]:
        invocation_parameters: dict[str, Any] = {}
        if payload.get("inferenceConfig"):
            invocation_parameters["inferenceConfig"] = payload["inferenceConfig"]
        if payload.get("toolConfig"):
            invocation_parameters["toolConfig"] = payload["toolConfig"]
        return invocation_parameters

    def _trace_tools(self, tools: list | None) -> list[dict[str, Any]] | None:
        trace_tools: list[dict[str, Any]] = []
        for tool in tools or []:
            if not isinstance(tool, dict):
                continue
            tool_spec = tool.get("toolSpec", {})
            if not isinstance(tool_spec, dict):
                continue

            input_schema = tool_spec.get("inputSchema", {})
            if isinstance(input_schema, dict) and "json" in input_schema:
                input_schema = input_schema.get("json", {})
            if not isinstance(input_schema, dict):
                input_schema = {"type": "object", "properties": {}}

            trace_tools.append(
                {
                    "json_schema": {
                        "type": "function",
                        "function": {
                            "name": tool_spec.get("name", ""),
                            "description": tool_spec.get("description", ""),
                            "parameters": input_schema,
                        },
                    }
                }
            )

        return trace_tools or None

    def _trace_output_messages(self, response: Any) -> list[dict[str, Any]] | None:
        if isinstance(response, dict):
            if message := self._trace_bedrock_output_message(response):
                return [message]
            if message := self._trace_azure_output_message_dict(response):
                return [message]

        choices = getattr(response, "choices", None)
        if choices:
            try:
                choice = choices[0]
            except Exception:
                choice = None
            if message := self._trace_azure_output_message_object(choice):
                return [message]

        return None

    def _trace_bedrock_output_message(self, response: dict[str, Any]) -> dict[str, Any] | None:
        content = response.get("output", {}).get("message", {}).get("content", [])
        if not isinstance(content, list):
            return None

        text_blocks: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text:
                text_blocks.append(text)
            tool_use = item.get("toolUse")
            if isinstance(tool_use, dict):
                tool_calls.append(
                    {
                        "id": tool_use.get("toolUseId", ""),
                        "function": {
                            "name": tool_use.get("name", ""),
                            "arguments": tool_use.get("input", {}),
                        },
                    }
                )

        if not text_blocks and not tool_calls:
            return None

        message: dict[str, Any] = {"role": "assistant"}
        if text_blocks:
            message["content"] = "\n".join(text_blocks)
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message

    def _trace_azure_output_message_dict(self, response: dict[str, Any]) -> dict[str, Any] | None:
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return None

        message_dict = choices[0].get("message", {})
        if not isinstance(message_dict, dict):
            return None

        message: dict[str, Any] = {"role": str(message_dict.get("role") or "assistant")}
        content = message_dict.get("content")
        if isinstance(content, str) and content:
            message["content"] = content

        tool_calls = self._normalize_tool_calls(message_dict.get("tool_calls"))
        if tool_calls:
            message["tool_calls"] = tool_calls

        if len(message) == 1:
            return None
        return message

    def _trace_azure_output_message_object(self, choice: Any) -> dict[str, Any] | None:
        if choice is None:
            return None

        message_obj = getattr(choice, "message", None)
        if message_obj is None:
            return None

        message: dict[str, Any] = {
            "role": str(getattr(message_obj, "role", None) or "assistant")
        }

        content = getattr(message_obj, "content", None)
        if isinstance(content, str) and content:
            message["content"] = content

        tool_calls = self._normalize_tool_calls(getattr(message_obj, "tool_calls", None))
        if tool_calls:
            message["tool_calls"] = tool_calls

        if len(message) == 1:
            return None
        return message

    def _normalize_tool_calls(self, tool_calls: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not tool_calls:
            return normalized

        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                function = tool_call.get("function", {})
                normalized.append(
                    {
                        "id": tool_call.get("id", ""),
                        "function": {
                            "name": function.get("name", ""),
                            "arguments": function.get("arguments", {}),
                        },
                    }
                )
                continue

            function = getattr(tool_call, "function", None)
            normalized.append(
                {
                    "id": getattr(tool_call, "id", ""),
                    "function": {
                        "name": getattr(function, "name", ""),
                        "arguments": getattr(function, "arguments", {}),
                    },
                }
            )

        return normalized

    def _trace_token_count(self, response: Any) -> dict[str, int] | None:
        usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        if usage is None:
            return None

        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens", usage.get("inputTokens"))
            completion_tokens = usage.get("completion_tokens", usage.get("outputTokens"))
            total_tokens = usage.get("total_tokens", usage.get("totalTokens"))
        else:
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            if prompt_tokens is None:
                prompt_tokens = getattr(usage, "inputTokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            if completion_tokens is None:
                completion_tokens = getattr(usage, "outputTokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
            if total_tokens is None:
                total_tokens = getattr(usage, "totalTokens", None)

        token_count = {
            key: value
            for key, value in {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
            }.items()
            if isinstance(value, int)
        }
        return token_count or None

    def _trace_output_value(
        self,
        response: Any,
        output_messages: list[dict[str, Any]] | None,
    ) -> Any:
        if output_messages:
            first_message = output_messages[0]
            content = first_message.get("content")
            if isinstance(content, str) and content:
                return content

            tool_calls = first_message.get("tool_calls")
            if tool_calls:
                return json.dumps(tool_calls, ensure_ascii=False)

        return response

    async def generate(self, prompt: str | list[dict[str, Any]], tools: list | None = None) -> Any:
        if not self.adapter:
            raise RuntimeError("LLM adapter not initialized; call init() first")
        if not self.model_id:
            raise RuntimeError("No model_id configured for LLM")
        tools = tools or []
        payload = self._build_model_payload(prompt, tools, None, 0.15, 256)

        with create_llm_span(
            self._llm_span_name(),
            model_name=self.model_name or self.model_id or self.model,
            provider=self.provider.value,
            input_value=self._trace_input_value(prompt),
            input_messages=self._trace_input_messages(prompt),
            invocation_parameters=self._trace_invocation_parameters(payload),
            tools=self._trace_tools(tools),
        ) as llm_span:
            response = await self.adapter.generate(payload)
            output_messages = self._trace_output_messages(response)
            set_llm_output(
                llm_span,
                output_value=self._trace_output_value(response, output_messages),
                output_messages=output_messages,
                token_count=self._trace_token_count(response),
            )
            return response

    def generate_sync(self, prompt: str | list[dict[str, Any]], tools: list | None = None) -> str:
        """Synchronous blocking wrapper for compatibility.

        Blocks the current thread while invoking the model. Prefer `await generate(...)`
        from async contexts.
        """
        if not self.adapter:
            raise RuntimeError("LLM adapter not initialized; call init() first")
        if not self.model_id:
            raise RuntimeError("No model_id configured for LLM")
        tools = tools or []
        payload = self._build_model_payload(prompt, tools, None, 0.15, 256)

        with create_llm_span(
            self._llm_span_name(),
            model_name=self.model_name or self.model_id or self.model,
            provider=self.provider.value,
            input_value=self._trace_input_value(prompt),
            input_messages=self._trace_input_messages(prompt),
            invocation_parameters=self._trace_invocation_parameters(payload),
            tools=self._trace_tools(tools),
        ) as llm_span:
            response = self.adapter.generate_sync(payload)
            output_messages = self._trace_output_messages(response)
            set_llm_output(
                llm_span,
                output_value=self._trace_output_value(response, output_messages),
                output_messages=output_messages,
                token_count=self._trace_token_count(response),
            )
            return response

    def _build_model_payload(self, prompt: str | list[dict[str, Any]], tools: list, model_family: Optional[str], temperature: float = 0.15, max_tokens: int = 100) -> dict:
        payload = {
            "messages": self._build_messages(prompt),
            "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
        }
        if tools:
            payload["toolConfig"] = {"tools": tools, "toolChoice": {"auto": {}}}
        return payload

    def _build_messages(self, prompt: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": [{"text": prompt}]}]

        messages: list[dict[str, Any]] = []
        for message in prompt:
            role = str(message.get("role") or "user").lower()
            if role not in {"user", "assistant"}:
                role = "user"

            content = message.get("content", "")
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append({"text": str(part.get("text") or "")})
                if not parts:
                    parts = [{"text": str(content)}]
            else:
                parts = [{"text": str(content)}]

            messages.append({"role": role, "content": parts})

        return messages or [{"role": "user", "content": [{"text": ""}]}]
