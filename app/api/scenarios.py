from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.scenario_service import list_available_scenarios, load_scenario

router = APIRouter(prefix="/scenarios", tags=["Synthetic Scenarios"])

@router.get("")
def get_scenarios():
    """Returns the list of 3 pre-packaged synthetic incident scenarios."""
    return list_available_scenarios()

@router.post("/{scenario_id}/load", status_code=status.HTTP_200_OK)
def import_scenario(scenario_id: str, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Loads and ingests a synthetic scenario deterministically."""
    try:
        res = load_scenario(db=db, scenario_id=scenario_id, actor=actor)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Scenario load failed: {str(ex)}")
