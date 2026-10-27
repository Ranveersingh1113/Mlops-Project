"""Stateless forecasting service. Only locally built, trusted artifacts are loaded."""
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator
from pypdf.errors import PyPdfError

from pipeline import ROOT, features
from observations import latest_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aqi")


def local_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


class Observation(BaseModel):
    date: date
    aqi: float = Field(ge=0, le=500, allow_inf_nan=False)


class ForecastInput(BaseModel):
    history: list[Observation] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def consecutive(self):
        if any(b.date - a.date != timedelta(days=1) for a, b in zip(self.history, self.history[1:])):
            raise ValueError("History must be seven consecutive dates, oldest first")
        if self.history[-1].date > local_today():
            raise ValueError("Future observations are not allowed")
        return self


def load_run():
    configured = os.getenv("MODEL_DIR")
    if configured:
        directory = Path(configured)
    else:
        run = json.loads((ROOT / "artifacts/latest.json").read_text())["run_id"]
        if not re.fullmatch(r"[a-f0-9]{32}", run):
            raise ValueError("Invalid trusted run pointer")
        directory = ROOT / "artifacts" / run
    report = json.loads((directory / "report.json").read_text())
    if not report["gate_passed"]:
        raise ValueError("Model failed baseline quality gate")
    model = joblib.load(directory / "model.joblib")
    probe = model.predict([features([100] * 7, date(2023, 1, 1))])
    if len(probe) != 1 or not np.isfinite(probe).all():
        raise ValueError("Model startup probe failed")
    return model, report


@asynccontextmanager
async def lifespan(application):
    try:
        application.state.model, application.state.report = load_run()
        application.state.error = None
    except (OSError, ValueError, KeyError) as exc:
        application.state.model = None
        application.state.error = str(exc)
        logger.error(json.dumps({"event": "model_load_failed", "error": str(exc)}))
    yield


app = FastAPI(title="Delhi AQI Forecasting", lifespan=lifespan)
app.state.model, app.state.report, app.state.error = None, None, "Train a model first"


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exception):
    # Raw nonfinite inputs cannot be serialized in the framework's default error body.
    # Return useful validation messages without echoing raw request values.
    detail = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
              for error in exception.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.middleware("http")
async def request_log(request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Request failed")
        raise
    logger.info(json.dumps({"event": "request", "path": request.url.path, "status": response.status_code,
                            "latency_ms": round((time.perf_counter() - started) * 1000, 2)}))
    return response


def require_model():
    if app.state.model is None:
        raise HTTPException(503, "Model unavailable; check startup logs and train a passing model")


def predict(data, model, report, today=None):
    target = data.history[-1].date + timedelta(days=1)
    history = [row.aqi for row in data.history]
    aqi = float(model.predict([features(history, target)])[0])
    if not np.isfinite(aqi) or not 0 <= aqi <= 500:
        raise ValueError("Model returned invalid AQI")
    today = today or local_today()
    return {"target_date": str(target), "aqi": round(aqi, 2), "model_version": report["run_id"],
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "historical_replay": target <= today, "input_age_days": (today - data.history[-1].date).days,
            "last_aqi": history[-1], "note": "City-average forecast; historical accuracy does not guarantee future accuracy."}


@app.get("/")
def dashboard():
    return FileResponse(ROOT / "dashboard.html")


@app.get("/health")
def health():
    require_model()
    return {"status": "ok", "model_version": app.state.report["run_id"]}


@app.get("/model")
def model_report():
    require_model()
    return app.state.report


@app.get("/observations/latest")
def recent_observations():
    try:
        result = latest_history()
    except (OSError, ValueError, PyPdfError) as exc:
        logger.error(json.dumps({"event": "source_fetch_failed", "error": str(exc)}))
        raise HTTPException(503, "CPCB observations unavailable; retry later or enter seven verified daily readings manually") from exc
    logger.info(json.dumps({"event": "observations_loaded", "sources": result["sources"]}))
    return result


@app.post("/predict")
def forecast(data: ForecastInput):
    require_model()
    result = predict(data, app.state.model, app.state.report)
    logger.info(json.dumps({"event": "forecast", "history": data.model_dump(mode="json")["history"], **result}))
    return result
