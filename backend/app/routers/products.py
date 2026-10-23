"""Products routes."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import get_current_user
from app.database import get_db
from app.models import LoanProduct
from app.schemas.products import ProductOut

router = APIRouter(prefix="/products", tags=["products"])

SORTS = {
    "rate_asc": (lambda p: (p.rate_min, p.id), False),
    "rate_desc": (lambda p: (p.rate_min, p.id), True),
    "amount_desc": (lambda p: (p.amount_max, p.id), True),
}


def matches(product: LoanProduct, q: str) -> bool:
    """Case-insensitive search in name, description and tags."""
    q = q.lower()
    haystack = [product.name, product.description, *product.tags]
    return any(q in text.lower() for text in haystack)


@router.get("", response_model=list[ProductOut])
def list_products(
    type: Optional[Literal["PERSONAL", "HOME", "VEHICLE", "EDUCATION"]] = None,
    q: Optional[str] = Query(None, max_length=100),
    sort: Literal["rate_asc", "rate_desc", "amount_desc"] = "rate_asc",
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Filter by loan type, search text, and sort. Only 8 products, so search/sort run in Python."""
    stmt = select(LoanProduct)
    if type:
        stmt = stmt.where(LoanProduct.loan_type == type)
    products = list(db.scalars(stmt))
    if q and q.strip():
        products = [p for p in products if matches(p, q.strip())]
    key, reverse = SORTS[sort]
    return sorted(products, key=key, reverse=reverse)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    product = db.get(LoanProduct, product_id)
    if product is None:
        raise AppError(404, "NOT_FOUND", "Product not found")
    return product
