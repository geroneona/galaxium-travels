from sqlalchemy.orm import Session
from models import Discount
from schemas import DiscountOut


def get_discount_by_booking_id(db: Session, booking_id: int) -> DiscountOut | None:
    """Get discount information for a specific booking."""
    discount = db.query(Discount).filter(Discount.booking_id == booking_id).first()
    if discount:
        return DiscountOut.model_validate(discount)
    return None


def get_all_discounts(db: Session) -> list[DiscountOut]:
    """Get all discount records."""
    discounts = db.query(Discount).all()
    return [DiscountOut.model_validate(d) for d in discounts]


def get_discounts_by_user_email(db: Session, email: str) -> list[DiscountOut]:
    """Get all discount records for a specific user by email."""
    discounts = db.query(Discount).filter(Discount.email == email).all()
    return [DiscountOut.model_validate(d) for d in discounts]

# Made with Bob
