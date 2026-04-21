"""
Agentic trip planner endpoint.

Accepts freeform goal text + lightweight trip hints, runs an OpenAI
function-calling loop that can invoke (search_flights, search_hotels,
get_weather, search_attractions, search_restaurants, estimate_budget,
compose_itinerary) and returns the full trace plus a final structured plan.

The heavy lifting lives in `services/agent_service.py`.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import Itinerary, User
from ..schemas import AgentPlanRequest, AgentPlanResponse
from ..services.agent_service import run_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/plan", response_model=AgentPlanResponse)
def plan(
    payload: AgentPlanRequest,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> AgentPlanResponse:
    result = run_agent(payload)

    # Persist the final plan so it appears in the user's itinerary history.
    if result.final_plan:
        it = Itinerary(
            user_id=user.id,
            trip_id=payload.trip_id,
            destination=result.final_plan.destination,
            days=len(result.final_plan.days),
            structured=result.final_plan.model_dump(),
            source="agent",
        )
        db.add(it)
        db.commit()

    return result
