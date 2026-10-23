"""The loan pipeline graph and run_pipeline().

START -> document -> credit -> compliance -> decide -> (request_docs | under_review) -> END
"""
from langgraph.graph import END, START, StateGraph

import app.agents.tools  # noqa: F401  (registers the tools)
from app.agents.nodes import (LoanState, compliance_agent, credit_agent, decide, document_agent, request_docs,
                              route, under_review)
from app.agents.registry import call_tool
from app.core.audit import log_audit
from app.core.errors import AppError
from app.models import AgentRun, AgentStep, Application
from app.schemas.pipeline import PipelineResult

CHECK_AGENTS = ("DocumentVerificationAgent", "CreditAssessmentAgent", "ComplianceAgent")


def build_graph():
    graph = StateGraph(LoanState)
    graph.add_node("document", document_agent)
    graph.add_node("credit", credit_agent)
    graph.add_node("compliance", compliance_agent)
    graph.add_node("decide", decide)
    graph.add_node("request_docs", request_docs)
    graph.add_node("under_review", under_review)
    graph.add_edge(START, "document")
    graph.add_edge("document", "credit")
    graph.add_edge("credit", "compliance")
    graph.add_edge("compliance", "decide")
    graph.add_conditional_edges("decide", route, {"request_docs": "request_docs", "under_review": "under_review"})
    graph.add_edge("request_docs", END)
    graph.add_edge("under_review", END)
    return graph.compile()


loan_graph = build_graph()


def _result(app: Application, run: AgentRun, state: dict) -> PipelineResult:
    checks = [{"agent": s["agent"], "result": s["result"], "detail": s["detail"]}
              for s in state["steps"] if s["agent"] in CHECK_AGENTS]
    return PipelineResult(
        application_id=app.code, recommendation=state["recommendation"], risk_band=state["risk_band"],
        checks=checks, missing_documents=state.get("missing_documents", []),
        customer_message=state["customer_message"], requires_human_approval=True,
        audit_trail_id=f"AUD-2026-{run.id:05d}",
    )


def run_pipeline(db, app_id: int) -> PipelineResult:
    """Run the agents for a SUBMITTED (first run) or UNDER_VERIFICATION (recheck) application."""
    app = db.get(Application, app_id)
    if app is None:
        raise AppError(404, "NOT_FOUND", "Application not found")
    if app.status == "SUBMITTED":
        call_tool(db, "Orchestrator", "update_application_status",
                  {"application_id": app.id, "new_status": "UNDER_VERIFICATION", "note": "Automated checks started"})
    elif app.status != "UNDER_VERIFICATION":
        raise AppError(409, "PIPELINE_NOT_ALLOWED", f"Checks can't run while the application is {app.status}")

    run = AgentRun(application_id=app.id, status="RUNNING", requires_human_approval=True)
    db.add(run)
    db.commit()
    run_id = run.id

    try:
        initial = {"application_id": app.id, "user_id": app.user_id, "loan_type": app.product.loan_type,
                   "amount": float(app.amount), "min_credit_score": app.product.min_credit_score, "steps": []}
        state = loan_graph.invoke(initial, config={"configurable": {"db": db}})

        for order, step in enumerate(state["steps"], start=1):
            db.add(AgentStep(run_id=run.id, step_order=order, agent_name=step["agent"], result=step["result"],
                             detail=step["detail"], tool_calls=step["tool_calls"]))
        result = _result(app, run, state)
        run.status = "COMPLETED"
        run.recommendation = result.recommendation
        run.risk_band = result.risk_band
        run.result_json = result.model_dump(by_alias=True)
        log_audit(db, action="PIPELINE_COMPLETED", actor="agent:Orchestrator", entity=f"application:{app.id}",
                  output={"recommendation": result.recommendation, "riskBand": result.risk_band,
                          "priority": state.get("priority"), "auditTrailId": result.audit_trail_id})
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        failed = db.get(AgentRun, run_id)
        failed.status = "FAILED"
        log_audit(db, action="PIPELINE_FAILED", status="ERROR", actor="agent:Orchestrator",
                  entity=f"application:{app_id}", output={"error": f"{type(exc).__name__}: {exc}"}, commit=True)
        raise AppError(500, "PIPELINE_FAILED", "Automated checks failed. Please click 'Re-run checks'.")
