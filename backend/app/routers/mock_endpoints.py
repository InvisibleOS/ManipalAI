from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from crud import placements as crud_placements

router = APIRouter(prefix="/mock", tags=["API Endpoints"])

@router.get("/placement-stats")
def get_placement_stats(db: Session = Depends(get_db)):
    stats = crud_placements.get_placement_stats(db)
    return {"status": "success", "data": stats}

@router.post("/placement-stats")
def create_placement_stat(stat_data: dict, db: Session = Depends(get_db)):
    new_stat = crud_placements.create_placement_stat(db, stat_data)
    return {"status": "success", "data": new_stat}

@router.post("/ai-chat")
def get_mock_ai_response(user_message: dict):
    return {
        "status": "success",
        "data": {"role": "ai", "message": "Placeholder.", "confidence_score": 0.95}
    }
