import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Point dotenv at the .env that lives next to this file (backend/.env) regardless
# of the current working directory, and re-read it with override so that a freshly
# edited key is picked up on the next request without restarting the server.
_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE, override=True)


class NIMClient:
    def __init__(self):
        # Re-read the env file fresh each time a client is created so a new key
        # in backend/.env is applied immediately (no backend restart needed).
        load_dotenv(_ENV_FILE, override=True)
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        
        if not self.api_key or self.api_key == "your_nvidia_nim_api_key_here":
            self.available = False
        else:
            self.available = True
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        if not self.available:
            return {
                "error": "NVIDIA NIM not configured. Set NVIDIA_API_KEY in .env file.",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "AI unavailable. NVIDIA NIM API key not configured. Please set NVIDIA_API_KEY in backend/.env file."
                    }
                }]
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"NIM API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": f"NIM request failed: {str(e)}"}


class ToolExecutor:
    def __init__(self, finance_tools):
        self.finance_tools = finance_tools
        self.tools = self._define_tools()
        self.tool_map = {
            "get_payment_summary": self.finance_tools.get_payment_summary,
            "list_payments": self.finance_tools.list_payments,
            "get_payment_details": self.finance_tools.get_payment_details,
            "get_pending_payments": self.finance_tools.get_pending_payments,
            "get_failed_payments": self.finance_tools.get_failed_payments,
            "get_refunds": self.finance_tools.get_refunds,
            "get_settlements": self.finance_tools.get_settlements,
            "reconcile_transaction": self.finance_tools.reconcile_transaction,
            "reconcile_batch": self.finance_tools.reconcile_batch,
            "find_exceptions": self.finance_tools.find_exceptions,
            "find_duplicates": self.finance_tools.find_duplicates,
            "calculate_cash_position": self.finance_tools.calculate_cash_position,
            "forecast_cash_flow": self.finance_tools.forecast_cash_flow,
            "get_finance_insights": self.finance_tools.get_finance_insights,
            "get_daily_finance_brief": self.finance_tools.get_daily_finance_brief,
            "get_money_flow": self.finance_tools.get_money_flow,
            "get_actions": self.finance_tools.get_actions,
        }
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_payment_summary",
                    "description": "Get overall payment summary with counts by status and success rate",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_payments",
                    "description": "List payments with optional status filter",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 100},
                            "status": {"type": "string", "enum": ["captured", "pending", "failed", "refunded", "authorized"]}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_payment_details",
                    "description": "Get detailed information for a specific payment including reconciliation status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "payment_id": {"type": "string"}
                        },
                        "required": ["payment_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pending_payments",
                    "description": "Get all pending payments",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_failed_payments",
                    "description": "Get all failed payments",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_refunds",
                    "description": "Get refund statistics and list",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 50}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_settlements",
                    "description": "Get settlement records",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 50}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reconcile_transaction",
                    "description": "Run reconciliation for a single transaction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "payment_id": {"type": "string"}
                        },
                        "required": ["payment_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reconcile_batch",
                    "description": "Run full batch reconciliation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 100}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_exceptions",
                    "description": "Find all exceptions requiring attention",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_duplicates",
                    "description": "Find potential duplicate payments",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_cash_position",
                    "description": "Calculate current cash position breakdown",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "forecast_cash_flow",
                    "description": "Forecast cash flow for specified days",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "default": 7}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_finance_insights",
                    "description": "Get data-driven business insights",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_daily_finance_brief",
                    "description": "Get daily finance brief with key metrics",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_money_flow",
                    "description": "Analyze where money went - complete money flow breakdown",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_actions",
                    "description": "Get available safe actions for exceptions",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.tool_map:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            func = self.tool_map[tool_name]
            result = func(**arguments)
            return {"result": _json_safe(result)}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for tc in tool_calls:
            name = tc["function"]["name"]
            raw_args = tc.get("function", {}).get("arguments", "")
            try:
                args = json.loads(raw_args) if raw_args else {}
            except (json.JSONDecodeError, TypeError):
                args = {}
            result = self.execute_tool(name, args)
            results.append({
                "tool_call_id": tc["id"],
                "tool": name,
                "arguments": args,
                "result": result
            })
        return results


def _json_safe(obj: Any) -> Any:
    """Recursively convert a tool result into a JSON-serializable structure.

    Some finance tools return SQLAlchemy ORM objects (e.g. find_exceptions returns
    a list of Exception models). Those are not directly serializable by json.dumps,
    which breaks feeding tool results back to NIM. This converts ORM objects to
    plain dicts and any other non-serializable value to a safe representation.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Exception):
        return str(obj)
    # SQLAlchemy ORM instances and other objects: try to serialize their attributes.
    try:
        if hasattr(obj, "_sa_instance_state"):
            return {k: _json_safe(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)
    except Exception:
        return str(obj)


def get_system_prompt() -> str:
    return """You are the AI Finance Controller for RazorLedger AI, a financial operations platform for merchants using Razorpay.

Your role is to act as a professional CFO-like analyst. You have access to real financial tools that query actual payment, settlement, refund, and reconciliation data.

CORE PRINCIPLES:
- NEVER invent financial numbers. Always use tools for factual questions.
- NEVER invent transactions or fabricate evidence.
- NEVER claim something is resolved without evidence.
- Distinguish facts from estimates clearly.
- Use Python/backend calculations for ALL financial arithmetic.
- Explain conclusions using actual retrieved data.
- Recommend concrete actions.
- Ask for confirmation before risky/irreversible actions.
- Be concise, professional, and analytical. Sound like a human CFO, not a chatbot.

TOOL USAGE:
- For "Where is my money?" → use get_money_flow, calculate_cash_position
- For "Why is settlement lower?" → use get_money_flow, get_settlements, get_refunds, reconcile_batch
- For "What needs attention?" → use find_exceptions, get_daily_finance_brief
- For "Show pending/failed" → use get_pending_payments, get_failed_payments
- For forecasts → use forecast_cash_flow
- For insights → use get_finance_insights
- For specific payment → use get_payment_details

RESPONSE FORMAT:
Provide grounded answers with:
1. Direct answer based on tool data
2. Key numbers from tools
3. Explanation of what the numbers mean
4. Recommended actions
5. Confidence level (based on data completeness)

When tools return data, cite specific numbers. When data is missing, say so clearly."""