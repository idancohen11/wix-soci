from fastapi import FastAPI, Query
from reddit_monitor import get_categorized_complaints

app = FastAPI()

@app.get("/complaints")
def get_complaints(limit: int = Query(20, ge=1, le=50)):
    """Return the latest categorized complaints from Reddit as JSON."""
    complaints = get_categorized_complaints(limit=limit)
    return {"complaints": complaints} 