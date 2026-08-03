"""mitmproxy addon: 抓包 → SSE 解码 → 脱敏 → 直接按甲方 spec 落盘

产出结构：
  ~/.mitmproxy/captured/{session_id}/{request_id}.json
  每个 JSON 是甲方 spec 格式（单行压缩、深度脱敏、无 localhost 痕迹）
"""
import os, json, time, re
from mitmproxy import http, ctx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURE_DIR = os.environ.get("CLAUDE_CAPTURE_DIR") or os.path.join(SCRIPT_DIR, "data")
os.makedirs(CAPTURE_DIR, exist_ok=True)

# Spec-compliant capture filter. Set CAPTURE_ALL=1 to disable (keep everything).
ALLOWED_MODELS = {
    "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8",
    "claude-opus-5", "claude-fable-5",
}
ALLOWED_EFFORTS = {"high", "xhigh", "max"}
CAPTURE_ALL = os.environ.get("CAPTURE_ALL") == "1"

# 深度脱敏：这些串出现在任何字段里都会被替换
REDACT_PATTERNS = [
    (re.compile(r"sk-ant-oat\d+-[A-Za-z0-9_\-]+"), "XXX_OAUTH_TOKEN_XXX"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "XXX_ANTHROPIC_KEY_XXX"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"), "Bearer XXX_TOKEN_XXX"),
]

_chunks: dict[str, list[bytes]] = {}


def _target(flow: http.HTTPFlow) -> bool:
    u = flow.request.url
    return ("/v1/messages" in u and "count_tokens" not in u)


def _extract_session_id(flow: http.HTTPFlow, req_body: dict) -> str:
    # 1) Claude Code 特有 header
    for h, v in flow.request.headers.items():
        if h.lower() == "x-claude-code-session-id":
            return v
    # 2) 甲方样例：metadata.user_id 里的 JSON 字符串
    try:
        uid = req_body.get("metadata", {}).get("user_id", "")
        sid = json.loads(uid).get("session_id")
        if sid: return sid
    except Exception:
        pass
    return "unknown-session"


def _parse_sse(sse_text: str):
    """SSE 事件流 → 完整的 Anthropic Messages API 响应结构"""
    msg, blocks = None, []
    stop_reason, stop_sequence = None, None
    usage = {}
    for line in sse_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"): continue
        payload = line[5:].strip()
        if not payload: continue
        try: evt = json.loads(payload)
        except: continue
        t = evt.get("type")
        if t == "message_start":
            msg = evt["message"]
            usage = msg.get("usage", {}) or {}
        elif t == "content_block_start":
            i = evt["index"]
            b = dict(evt["content_block"])
            while len(blocks) <= i: blocks.append({})
            blocks[i] = b
            if b.get("type") == "text": b.setdefault("text", "")
            if b.get("type") == "thinking": b.setdefault("thinking", "")
            if b.get("type") == "tool_use":
                b["input"] = {}
                b["_partial"] = ""
        elif t == "content_block_delta":
            i = evt["index"]
            d = evt["delta"]
            dt = d.get("type")
            if dt == "text_delta":        blocks[i]["text"] += d["text"]
            elif dt == "thinking_delta":  blocks[i]["thinking"] += d["thinking"]
            elif dt == "signature_delta": blocks[i]["signature"] = d["signature"]
            elif dt == "input_json_delta":blocks[i]["_partial"] += d["partial_json"]
        elif t == "content_block_stop":
            i = evt["index"]
            if "_partial" in blocks[i]:
                try: blocks[i]["input"] = json.loads(blocks[i]["_partial"])
                except: blocks[i]["input"] = {}
                del blocks[i]["_partial"]
        elif t == "message_delta":
            d = evt.get("delta", {})
            stop_reason = d.get("stop_reason", stop_reason)
            stop_sequence = d.get("stop_sequence", stop_sequence)
            if "usage" in evt: usage.update(evt["usage"])
    if not msg: return None
    msg["content"] = blocks
    msg["stop_reason"] = stop_reason
    msg["stop_sequence"] = stop_sequence
    msg["usage"] = usage
    return msg


def _redact(text: str) -> str:
    if not text: return text
    for pat, rep in REDACT_PATTERNS:
        text = pat.sub(rep, text)
    return text


def _redact_deep(obj):
    if isinstance(obj, str):
        return _redact(obj)
    if isinstance(obj, dict):
        return {k: _redact_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_deep(x) for x in obj]
    return obj


def request(flow: http.HTTPFlow):
    """请求发出前：去掉压缩要求，让 Anthropic 返回明文 SSE"""
    if _target(flow):
        flow.request.headers.pop("accept-encoding", None)


def responseheaders(flow: http.HTTPFlow):
    """SSE 流式转发不阻塞 Claude Code UI"""
    if not _target(flow):
        return
    ct = flow.response.headers.get("content-type", "")
    if "text/event-stream" in ct:
        _chunks[flow.id] = []
        def tap(chunk: bytes) -> bytes:
            _chunks[flow.id].append(chunk)
            return chunk
        flow.response.stream = tap


def response(flow: http.HTTPFlow):
    if not _target(flow):
        return

    # Parse request body first — we may need to skip based on model/effort
    try:
        req_body = json.loads(flow.request.get_text(strict=False))
    except Exception as e:
        _chunks.pop(flow.id, None)
        ctx.log.warn(f"[skip] request body is not valid JSON: {e}")
        return

    # Filter: skip Claude Code's internal helper calls (Haiku title-gen, suggestion, etc.)
    # These use non-spec models or thinking=disabled and are useless for delivery.
    if not CAPTURE_ALL:
        model = req_body.get("model", "")
        thinking_type = req_body.get("thinking", {}).get("type", "")
        effort = req_body.get("output_config", {}).get("effort", "")
        if model not in ALLOWED_MODELS:
            _chunks.pop(flow.id, None)
            ctx.log.info(f"[skip] non-spec model: {model}")
            return
        if thinking_type != "adaptive":
            _chunks.pop(flow.id, None)
            ctx.log.info(f"[skip] thinking type: {thinking_type}")
            return
        if effort not in ALLOWED_EFFORTS:
            _chunks.pop(flow.id, None)
            ctx.log.info(f"[skip] non-spec effort: {effort}")
            return

    # Collect the full response body
    if flow.id in _chunks:
        body = b"".join(_chunks.pop(flow.id)).decode("utf-8", errors="replace")
    else:
        body = flow.response.get_text(strict=False)

    # 解析 SSE
    resp_data = _parse_sse(body)
    if not resp_data:
        ctx.log.warn(f"[skip] SSE 解码失败")
        return

    # 元数据
    sid = _extract_session_id(flow, req_body)
    rid = flow.response.headers.get("request-id", flow.id)
    effort = req_body.get("output_config", {}).get("effort", "unknown")

    # 甲方 spec 格式（不含 URL / headers / localhost 任何痕迹）
    record = {
        "session_id": sid,
        "request_id": rid,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "thinking_effort": effort,
        "is_garbled": False,
        "request": req_body,
        "response": {"response_data": resp_data},
    }
    # 深度脱敏
    record = _redact_deep(record)

    # 按 session 归类 + 单行压缩
    session_dir = os.path.join(CAPTURE_DIR, sid)
    os.makedirs(session_dir, exist_ok=True)
    path = os.path.join(session_dir, f"{rid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
    ctx.log.info(f"[saved] {sid[:8]}/{rid} model={record['request'].get('model')} effort={effort}")
