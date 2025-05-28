from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from reddit_monitor import get_categorized_complaints

app = FastAPI()

# Add CORS middleware to allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/complaints")
def get_complaints(limit: int = Query(20, ge=1, le=100)):
    """Return the latest categorized complaints from Reddit as JSON."""
    complaints = get_categorized_complaints(limit=limit)
    return {"complaints": complaints} 