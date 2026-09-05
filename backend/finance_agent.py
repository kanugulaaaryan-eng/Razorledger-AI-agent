import json
from typing import List, Dict, Any
from nim_client import NIMClient, ToolExecutor, get_system_prompt
from finance_tools import FinanceTools
from models import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime


class FinanceAgent:
    def __init__(self, db: Session):
        self.db = db
        self.finance_tools = FinanceTools(db)
        self.nim_client = NIMClient()
        self.tool_executor = ToolExecutor(self.finance_tools)
    
    def chat(self, message: str) -> Dict[str, Any]:
        if not self.nim_client.available:
            return self._fallback_response(message)
        
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": message}
        ]
        
        tools_used = []
        tool_results = []
        audit_data = {
            "question": message,
            "tools_used": [],
            "records_inspected": 0,
            "calculations": [],
            "evidence": [],
            "decision": "",
            "confidence": 0.0,
            "recommended_action": ""
        }
        
        max_iterations = 6
        final_response = ""
        for iteration in range(max_iterations):
            response = self.nim_client.chat_completion(
                messages=messages,
                tools=self.tool_executor.tools,
                tool_choice="auto"
            )
            
            if "error" in response:
                return self._fallback_response(message, error=response["error"])
            
            choice = response["choices"][0]
            message_obj = choice["message"]
            
            if message_obj.get("tool_calls"):
                tools_used.extend([tc["function"]["name"] for tc in message_obj["tool_calls"]])
                audit_data["tools_used"] = tools_used
                
                executed_results = self.tool_executor.execute_tool_calls(message_obj["tool_calls"])
                
                for er in executed_results:
                    tool_results.append({
                        "tool": er["tool"],
                        "arguments": er["arguments"],
                        "result": er["result"]
                    })
                    
                    if "result" in er["result"] and er["result"]["result"]:
                        result_data = er["result"]["result"]
                        if isinstance(result_data, list):
                            audit_data["records_inspected"] += len(result_data)
                        elif isinstance(result_data, dict):
                            audit_data["records_inspected"] += 1
                            if "total_payments" in result_data:
                                audit_data["calculations"].append(f"Payment summary: {result_data['total_payments']} total")
                            if "total_expected" in result_data:
                                audit_data["calculations"].append(f"Forecast: ₹{result_data['total_expected']:,.2f} expected")
                            if "total_count" in result_data:
                                audit_data["calculations"].append(f"Refunds: {result_data['total_count']} totaling ₹{result_data['total_amount']:,.2f}")
                
                messages.append(message_obj)
                for er in executed_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": er["tool_call_id"],
                        "content": json.dumps(er["result"])
                    })
            else:
                messages.append(message_obj)
                final_response = message_obj.get("content", "")
                
                audit_data["decision"] = final_response[:200]
                audit_data["confidence"] = 0.85 if tools_used else 0.3
                audit_data["recommended_action"] = "Review evidence panel for details"
                break
        
        if not final_response and tool_results:
            # Model exhausted its iterations without emitting a final text answer.
            # Never return an empty response: build a concise summary strictly from
            # the real tool results already retrieved (no fabricated numbers).
            final_response = self._summarize_tool_results(tool_results)
            audit_data["decision"] = final_response[:200]
            audit_data["confidence"] = 0.6

        self._save_audit_log(audit_data)
        
        return {
            "response": final_response,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "audit_trail": audit_data
        }

    def _summarize_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        # Builds a grounded, human-readable summary from the actual tool results.
        # Only reads numbers that are present in the retrieved data.
        lines = []
        for tr in tool_results:
            res = tr.get("result") or {}
            data = res.get("result")
            tool = tr.get("tool")
            if tool == "calculate_cash_position" and isinstance(data, dict):
                lines.append(
                    f"Cash position: captured ₹{data.get('captured_total', 0):,.2f}, "
                    f"settled ₹{data.get('settled_cash', 0):,.2f}, "
                    f"pending ₹{data.get('pending_settlement', 0):,.2f}, "
                    f"refunded ₹{data.get('refunded', 0):,.2f}, "
                    f"unresolved ₹{data.get('unresolved', 0):,.2f}."
                )
            elif tool == "get_money_flow" and isinstance(data, dict):
                lines.append(f"Money flow: {data.get('explanation', '')}")
            elif tool == "get_refunds" and isinstance(data, dict):
                lines.append(
                    f"Refunds: {data.get('total_count', 0)} totaling "
                    f"₹{data.get('total_amount', 0):,.2f}."
                )
            elif tool == "get_pending_payments" and isinstance(data, list):
                lines.append(f"Pending payments: {len(data)}.")
            elif tool == "find_exceptions" and isinstance(data, list):
                lines.append(f"Open exceptions requiring attention: {len(data)}.")
            elif tool == "get_daily_finance_brief" and isinstance(data, dict):
                lines.append(
                    f"Daily brief: collected today ₹{data.get('collected', 0):,.2f}, "
                    f"success rate {data.get('success_rate', 0)}%, "
                    f"match rate {data.get('match_rate', 0)}%."
                )
        if lines:
            return "Here are the verified ledger results:\n\n" + "\n".join(lines)
        return "The analysis completed. See the tool results for details."
    
    def _fallback_response(self, message: str, error: str = None) -> Dict[str, Any]:
        tools_used = []
        tool_results = []
        
        if "money" in message.lower() or "cash" in message.lower():
            cash = self.finance_tools.calculate_cash_position()
            money_flow = self.finance_tools.get_money_flow()
            tools_used = ["calculate_cash_position", "get_money_flow"]
            tool_results = [
                {"tool": "calculate_cash_position", "result": cash},
                {"tool": "get_money_flow", "result": money_flow}
            ]
            response = f"""AI unavailable. Here are the verified ledger results:

**Cash Position:**
- Captured Total: ₹{cash['captured_total']:,.2f}
- Settled Cash: ₹{cash['settled_cash']:,.2f}
- Available Cash: ₹{cash['available_cash']:,.2f}
- Pending Settlement: ₹{cash['pending_settlement']:,.2f}
- Refunded: ₹{cash['refunded']:,.2f}
- Fees Paid: ₹{cash['fees_paid']:,.2f}
- Unresolved: ₹{cash['unresolved']:,.2f}

**Money Flow:**
{money_flow['explanation']}

Configure NVIDIA_API_KEY in backend/.env to enable AI analysis."""
        elif "settlement" in message.lower():
            settlements = self.finance_tools.get_settlements(10)
            refunds = self.finance_tools.get_refunds(10)
            tools_used = ["get_settlements", "get_refunds"]
            tool_results = [
                {"tool": "get_settlements", "result": settlements},
                {"tool": "get_refunds", "result": refunds}
            ]
            response = f"""AI unavailable. Here are the verified ledger results:

**Recent Settlements:**
{len(settlements)} settlements retrieved. Total discrepancies: ₹{sum(s['discrepancy'] for s in settlements):,.2f}

**Recent Refunds:**
{refunds['total_count']} refunds totaling ₹{refunds['total_amount']:,.2f}

Configure NVIDIA_API_KEY in backend/.env to enable AI analysis."""
        elif "exception" in message.lower() or "attention" in message.lower():
            exceptions = self.finance_tools.find_exceptions()
            tools_used = ["find_exceptions"]
            tool_results = [{"tool": "find_exceptions", "result": [{"exception_id": e.exception_id, "type": e.exception_type, "severity": e.severity.value, "amount": e.amount, "reason": e.reason} for e in exceptions]}]
            response = f"""AI unavailable. Here are the verified ledger results:

**Open Exceptions: {len(exceptions)}**
"""
            for e in exceptions[:10]:
                response += f"- [{e.severity.value.upper()}] {e.exception_type}: {e.reason} (₹{e.amount:,.2f})\n"
            response += "\nConfigure NVIDIA_API_KEY in backend/.env to enable AI analysis."
        else:
            brief = self.finance_tools.get_daily_finance_brief()
            tools_used = ["get_daily_finance_brief"]
            tool_results = [{"tool": "get_daily_finance_brief", "result": brief}]
            response = f"""AI unavailable. Here is your daily finance brief:

**{brief['greeting']}**
- Collected today: ₹{brief['collected']:,.2f}
- Success rate: {brief['success_rate']}%
- Refunded: ₹{brief['refunded']:,.2f}
- Pending: ₹{brief['pending_settlement']:,.2f}
- Match rate: {brief['match_rate']}%

**Top Priorities:**
"""
            for p in brief['top_priorities']:
                response += f"• {p}\n"
            response += "\nConfigure NVIDIA_API_KEY in backend/.env to enable AI analysis."
        
        # Surface WHY the AI path was unavailable so the issue is easy to fix.
        if error:
            response += f"\n\nAI diagnostics: {error}"

        audit_data = {
            "question": message,
            "tools_used": tools_used,
            "records_inspected": sum(len(r["result"]) if isinstance(r["result"], list) else 1 for r in tool_results),
            "calculations": ["Verified backend data"],
            "evidence": ["Fallback mode - AI unavailable"],
            "decision": response[:200],
            "confidence": 0.5,
            "recommended_action": "Configure NVIDIA_API_KEY for full AI analysis"
        }
        self._save_audit_log(audit_data)
        
        return {
            "response": response,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "audit_trail": audit_data
        }
    
    def _save_audit_log(self, audit_data: Dict[str, Any]):
        try:
            log = AuditLog(
                question=audit_data["question"],
                tools_used=audit_data["tools_used"],
                records_inspected=audit_data["records_inspected"],
                calculations=audit_data["calculations"],
                evidence=audit_data["evidence"],
                decision=audit_data["decision"],
                confidence=audit_data["confidence"],
                recommended_action=audit_data["recommended_action"],
                is_synthetic=1
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()