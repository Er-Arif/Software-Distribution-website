from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.db.models import LegalDocument, Plan, Product, ReleaseNote
from app.schemas import PlanOut, ProductOut

router = APIRouter(dependencies=[Depends(rate_limit("public"))])


@router.get("/products", response_model=list[ProductOut])
def products(db: Session = Depends(get_db)) -> list[Product]:
    return list(
        db.scalars(
            select(Product).where(Product.status == "published", Product.deleted_at.is_(None)).order_by(Product.name)
        )
    )


@router.get("/products/{slug}")
def product_detail(slug: str, db: Session = Depends(get_db)) -> dict:
    product = db.scalar(select(Product).where(Product.slug == slug, Product.deleted_at.is_(None)))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    plans = db.scalars(select(Plan).where(Plan.product_id == product.id, Plan.deleted_at.is_(None))).all()
    return {"product": ProductOut.model_validate(product), "plans": [PlanOut.model_validate(plan) for plan in plans]}


@router.get("/legal/{document_type}")
def legal(document_type: str, db: Session = Depends(get_db)) -> dict:
    doc = db.scalar(
        select(LegalDocument)
        .where(
            LegalDocument.document_type == document_type,
            LegalDocument.deleted_at.is_(None),
            LegalDocument.published_at.is_not(None),
        )
        .order_by(LegalDocument.published_at.desc())
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Legal document not found")
    return {"title": doc.title, "version": doc.version, "body": doc.body}


@router.get("/changelog")
def changelog(db: Session = Depends(get_db)) -> list[dict]:
    notes = db.scalars(select(ReleaseNote).where(ReleaseNote.deleted_at.is_(None)).order_by(ReleaseNote.created_at.desc())).all()
    return [{"title": note.title, "body": note.body, "visibility": note.visibility} for note in notes]
