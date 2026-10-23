"""LangGraph nodes. Rules live in code; the LLM only writes the customer message.

Every node reads the DB session from config and touches data only through call_tool.
"""
import operator
from typing import Annotated, Optional, TypedDict

from langchain_core.runnables import RunnableConfig

from app.agents.registry import call_tool
from app.core.llm import chat
from app.core.pii import mask_pii
from app.models import DOC_LABELS, DOC_TYPES
from app.services.emi import format_inr

HIGH_VALUE_AMOUNT = 1000000  # ₹10 lakh


class LoanState(TypedDict, total=False):
    application_id: int
    user_id: int
    loan_type: str
    amount: float
    min_credit_score: int
    steps: Annotated[list, operator.add]
    missing_documents: list[str]
    credit: dict
    foir: float
    risk_band: str
    recommendation: str
    priority: bool
    customer_message: str


class ToolRecorder:
    """Calls tools for one agent and remembers each call for the step's tool_calls."""

    def __init__(self, db, agent: str):
        self.db, self.agent, self.calls = db, agent, []

    def __call__(self, tool: str, **args):
        result = call_tool(self.db, self.agent, tool, args)
        self.calls.append({"tool": tool, "args": args, "result": result})
        return result


def _db(config: RunnableConfig):
    return config["configurable"]["db"]


def _step(agent: str, result: str, detail: str, tools: ToolRecorder) -> dict:
    return {"agent": agent, "result": result, "detail": detail, "tool_calls": tools.calls}


def _join_labels(labels: list[str]) -> str:
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]


# ---------- pure decision helpers (unit-tested) ----------

def risk_band(score: int, foir: float) -> str:
    """LOW if score >= 760 and FOIR <= 40; HIGH if score < 650 or FOIR > 50; otherwise MEDIUM."""
    if score < 650 or foir > 50:
        return "HIGH"
    if score >= 760 and foir <= 40:
        return "LOW"
    return "MEDIUM"


def decide_recommendation(checks: list[dict], missing_docs: list[str], risk: str) -> str:
    """Missing docs first; any FAIL/MISMATCH -> reject if HIGH else manual; all pass + LOW -> approve."""
    if missing_docs:
        return "REQUEST_ADDITIONAL_DOCUMENTS"
    results = {c["result"] for c in checks}
    if results & {"FAIL", "MISMATCH"}:
        return "RECOMMEND_REJECT" if risk == "HIGH" else "MANUAL_REVIEW"
    if results == {"PASS"} and risk == "LOW":
        return "RECOMMEND_APPROVE"
    return "MANUAL_REVIEW"


def is_priority(amount: float, risk: str, checks: list[dict]) -> bool:
    return amount > HIGH_VALUE_AMOUNT or risk != "LOW" or any(c["result"] != "PASS" for c in checks)


# ---------- agent nodes ----------

def document_agent(state: LoanState, config: RunnableConfig) -> dict:
    tools = ToolRecorder(_db(config), "DocumentVerificationAgent")
    app_id = state["application_id"]
    uploaded = set(tools("get_documents", application_id=app_id))
    missing = [DOC_LABELS[t] for t in DOC_TYPES if t not in uploaded]

    if missing:
        verb = "is" if len(missing) == 1 else "are"
        result, detail = "INCOMPLETE", f"{_join_labels(missing)} {verb} missing"
    else:
        income = tools("verify_income", application_id=app_id)
        if income["ok"]:
            result, detail = "PASS", "All required documents present; income verified"
        elif income["verified"] is None:
            result, detail = "MISMATCH", "Income could not be verified from the uploaded documents"
        else:
            result = "MISMATCH"
            detail = (f"Declared income {format_inr(income['declared'])} differs from verified "
                      f"{format_inr(income['verified'])} by {income['mismatchPct']}% (limit 10%)")

    return {"steps": [_step("DocumentVerificationAgent", result, detail, tools)], "missing_documents": missing}


def credit_agent(state: LoanState, config: RunnableConfig) -> dict:
    tools = ToolRecorder(_db(config), "CreditAssessmentAgent")
    credit = tools("get_credit_score", user_id=state["user_id"])
    foir = tools("calc_foir", application_id=state["application_id"])["foir"]
    ok = credit["score"] >= state["min_credit_score"] and foir <= 50
    detail = f"Obligation ratio is {foir}% (limit 50%); credit score band is {credit['bandRange']} ({credit['band']})"
    if credit["score"] < state["min_credit_score"]:
        detail += f"; below the product minimum score of {state['min_credit_score']}"
    return {"steps": [_step("CreditAssessmentAgent", "PASS" if ok else "FAIL", detail, tools)],
            "credit": credit, "foir": foir}


def compliance_agent(state: LoanState, config: RunnableConfig) -> dict:
    tools = ToolRecorder(_db(config), "ComplianceAgent")
    kyc = tools("get_kyc_status", user_id=state["user_id"])["status"]
    policy = tools("policy_lookup", loan_type=state["loan_type"])
    if kyc == "VERIFIED":
        result, detail = "PASS", "KYC status verified"
    else:
        result, detail = "FAIL", f"KYC status is {kyc}"
    if policy:
        detail += f" · Policy ref: {policy['document']} v{policy['version']}"
    return {"steps": [_step("ComplianceAgent", result, detail, tools)]}


def decide(state: LoanState, config: RunnableConfig) -> dict:
    """Orchestrator: risk band + recommendation, then hand to a human (UNDER_REVIEW). It can never approve."""
    tools = ToolRecorder(_db(config), "Orchestrator")
    checks = [s for s in state["steps"] if s["agent"] != "Orchestrator"]
    risk = risk_band(state["credit"]["score"], state["foir"])
    recommendation = decide_recommendation(checks, state.get("missing_documents", []), risk)
    priority = is_priority(state["amount"], risk, checks)
    tools("update_application_status", application_id=state["application_id"], new_status="UNDER_REVIEW",
          note=f"Automated checks complete: {recommendation}")
    detail = f"Risk {risk}; requires human approval" + ("; priority review" if priority else "")
    return {"steps": [_step("Orchestrator", recommendation, detail, tools)],
            "risk_band": risk, "recommendation": recommendation, "priority": priority}


def route(state: LoanState) -> str:
    return "request_docs" if state.get("missing_documents") else "under_review"


COMMS_PROMPT = ("Write a short, polite, plain-language status update for a bank customer in 1–2 sentences. "
                "Never promise approval. No personal identifiers.")


def _communicate(state: LoanState, summary: str, fallback: str) -> dict:
    tools = ToolRecorder(None, "CustomerCommunicationAgent")  # no tools allowed
    try:
        message = chat(COMMS_PROMPT, mask_pii(summary)) or fallback
    except Exception:
        message = fallback
    return {"steps": [_step("CustomerCommunicationAgent", "SENT", message, tools)], "customer_message": message}


def request_docs(state: LoanState, config: RunnableConfig) -> dict:
    docs = _join_labels(state["missing_documents"]).lower()
    fallback = f"Please upload a valid {docs} to continue your application."
    summary = f"The loan application is waiting for these documents: {docs}. Ask the customer to upload them."
    return _communicate(state, summary, fallback)


def under_review(state: LoanState, config: RunnableConfig) -> dict:
    fallback = "Your application has passed our automated checks and is now with a credit analyst for review."
    summary = "The loan application finished automated checks and is now with a human credit analyst for review."
    return _communicate(state, summary, fallback)
