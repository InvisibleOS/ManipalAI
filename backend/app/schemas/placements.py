from pydantic import BaseModel
from typing import Optional

class PlacementQuery(BaseModel):
    """
    Template for the frontend requesting specific placement data.
    """
    company_name: Optional[str] = None
    branch: Optional[str] = "ECE"  # Defaulting to core branches for baseline metrics
    year: Optional[int] = None

class PlacementStat(BaseModel):
    """
    Template for returning the fetched placement metrics.
    """
    company_name: str
    students_placed: int
    highest_ctc: float
    average_ctc: float