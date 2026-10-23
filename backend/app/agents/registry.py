"""Tool registry with per-agent allowlists. Every call is audited; disallowed calls are denied and audited."""
from app.core.audit import log_audit

TOOLS: dict = {}

AGENT_PERMISSIONS = {
    "DocumentVerificationAgent": {"get_documents", "verify_income"},
    "CreditAssessmentAgent": {"get_credit_score", "calc_foir"},
    "ComplianceAgent": {"get_kyc_status", "policy_lookup"},
    "Orchestrator": {"update_application_status"},
    "CustomerCommunicationAgent": set(),
}


class ToolPermissionError(Exception):
    """An agent tried to use a tool outside its allowlist."""


def register_tool(name: str):
    """Decorator: make a function callable through call_tool under this name."""
    def decorator(fn):
        TOOLS[name] = fn
        return fn
    return decorator


def is_tool_allowed(agent: str, tool: str) -> bool:
    return tool in AGENT_PERMISSIONS.get(agent, set())


def call_tool(db, agent: str, tool: str, args: dict, application_id: int | None = None):
    """Run a tool on behalf of an agent, enforcing the allowlist. application_id links the audit row."""
    actor = f"agent:{agent}"
    app_id = application_id or args.get("application_id")
    entity = f"application:{app_id}" if app_id else None
    if not is_tool_allowed(agent, tool) or tool not in TOOLS:
        log_audit(db, action="TOOL_DENIED", status="DENIED", actor=actor, entity=entity,
                  input={"tool": tool, "args": args}, commit=True)
        raise ToolPermissionError(f"{agent} is not allowed to use {tool}")
    result = TOOLS[tool](db, **args)
    log_audit(db, action="TOOL_CALL", actor=actor, entity=entity, input={"tool": tool, "args": args}, output=result)
    return result
