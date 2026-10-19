"""Rota de saúde: confirma que a API está no ar e consegue falar com o banco."""

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from venergy_api.database import SessionDep

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health(session: SessionDep, response: Response) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # 503, e não 500: a API está de pé, mas uma dependência dela (o banco) não está.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
