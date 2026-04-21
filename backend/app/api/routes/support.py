from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user, require_roles
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


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    messages = db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == ticket.id).order_by(TicketMessage.created_at)).all()
    return {
        "id": str(ticket.id),
        "subject": ticket.subject,
        "status": ticket.status,
        "messages": [{"author_id": str(msg.author_id), "body": msg.body, "created_at": msg.created_at} for msg in messages],
    }


@router.post("/tickets/{ticket_id}/reply")
def customer_reply(ticket_id: UUID, body: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.add(TicketMessage(ticket_id=ticket.id, author_id=user.id, body=body))
    emit_event(db, "support.customer_replied", "support_ticket", str(ticket.id), {})
    db.commit()
    return {"status": "sent"}


@router.post("/admin/tickets/{ticket_id}/reply")
def staff_reply(
    ticket_id: UUID,
    body: str,
    staff: User = Depends(require_roles("super_admin", "admin", "support")),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.add(TicketMessage(ticket_id=ticket.id, author_id=staff.id, body=body))
    ticket.status = "waiting_on_customer"
    emit_event(db, "support.staff_replied", "support_ticket", str(ticket.id), {})
    db.commit()
    return {"status": "sent"}
