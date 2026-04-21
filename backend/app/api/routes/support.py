from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import SupportTicket, TicketMessage, User
from app.schemas import SupportTicketCreate
from app.services.events import emit_event

router = APIRouter()


@router.post("/tickets")
def create_ticket(payload: SupportTicketCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ticket = SupportTicket(user_id=user.id, product_id=payload.product_id, subject=payload.subject, priority=payload.priority)
    db.add(ticket)
    db.flush()
    db.add(TicketMessage(ticket_id=ticket.id, author_id=user.id, body=payload.body))
    emit_event(db, "support.ticket_created", "support_ticket", str(ticket.id), {})
    db.commit()
    return {"id": str(ticket.id), "status": ticket.status}
