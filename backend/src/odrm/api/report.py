from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from odrm.api.schemas import TeaRequest
from odrm.api.screening import run_screening
from odrm.auth.dependencies import get_current_user
from odrm.domain.tea import TeaCalculationError, TeaInputError
from odrm.reporting.content import build_report_data
from odrm.reporting.pdf import render_pdf
from odrm.services.prediction import (
    ModelUnavailableError,
    PredictionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

EXPOSED_HEADERS = (
    "Content-Disposition",
    "X-Report-Id",
    "X-Report-SHA256",
    "X-Report-Generated-At",
)


@router.post(
    "/report",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "ESG screening report PDF with integrity headers.",
        }
    },
)
def report(request: TeaRequest, req: Request) -> Response:
    report_id = str(uuid4())
    try:
        screening = run_screening(request, req.app.state.models)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail="Model prediction failed.") from exc
    except TeaInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TeaCalculationError as exc:
        raise HTTPException(status_code=500, detail="TEA calculation failed.") from exc

    generated_at = datetime.now(UTC).replace(microsecond=0)
    try:
        report_data = build_report_data(
            request,
            screening,
            report_id=report_id,
            generated_at=generated_at,
        )
        pdf_bytes = render_pdf(report_data)
    except Exception as exc:
        logger.exception("Report generation failed report_id=%s", report_id)
        raise HTTPException(status_code=500, detail="Report generation failed.") from exc

    headers = {
        "Content-Disposition": (
            f'attachment; filename="odrm-esg-report-{report_data.report_id}.pdf"'
        ),
        "X-Report-Id": report_data.report_id,
        "X-Report-SHA256": report_data.sha256,
        "X-Report-Generated-At": report_data.generated_at,
    }
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )
