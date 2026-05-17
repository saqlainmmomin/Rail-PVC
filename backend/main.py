from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api import bills, carry_forwards, contracts, documents, extra_items, indices, pvc_rules, pvc_runs, schedules

app = FastAPI(
    title="RailPVC API",
    description="Billing OS for Indian Railway contractors — PVC calculation engine API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "railpvc-api"}


app.include_router(contracts.router)
app.include_router(schedules.router)
app.include_router(bills.router)
app.include_router(carry_forwards.router)
app.include_router(indices.router)
app.include_router(extra_items.router)
app.include_router(pvc_rules.router)
app.include_router(pvc_runs.router)
app.include_router(documents.router)
