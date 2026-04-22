from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import checksum_bytes, storage_service
from app.db.models import FileMetadata, InvoiceRecord, Order, Payment, User


def render_invoice_pdf(invoice: InvoiceRecord, order: Order, payment: Payment | None, user: User) -> bytes:
    body = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        f"4 0 obj << /Length 220 >> stream\nBT /F1 12 Tf 50 740 Td (Invoice {invoice.invoice_number}) Tj "
        f"0 -20 Td (Customer {user.email}) Tj 0 -20 Td (Order {order.id}) Tj "
        f"0 -20 Td (Payment {payment.provider_payment_id if payment else 'N/A'}) Tj "
        f"0 -20 Td (Total {float(order.total_amount)} {order.currency}) Tj "
        f"0 -20 Td (Issued {datetime.now(UTC).date().isoformat()}) Tj ET\nendstream endobj\n"
        "xref\n0 5\n0000000000 65535 f \ntrailer << /Root 1 0 R /Size 5 >>\nstartxref\n0\n%%EOF\n"
    )
    return body.encode("utf-8")


def attach_invoice_pdf(db: Session, invoice: InvoiceRecord, order: Order, payment: Payment | None, user: User) -> FileMetadata:
    data = render_invoice_pdf(invoice, order, payment, user)
    object_key = f"invoices/{invoice.invoice_number}.pdf"
    storage_service.upload_bytes(settings.s3_private_installers_bucket, object_key, data, "application/pdf")
    file_obj = FileMetadata(
        bucket=settings.s3_private_installers_bucket,
        object_key=object_key,
        visibility="private",
        mime_type="application/pdf",
        size_bytes=len(data),
        sha256=checksum_bytes(data),
        scan_status="trusted",
        context={"invoice_id": str(invoice.id)},
    )
    db.add(file_obj)
    db.flush()
    invoice.pdf_file_id = file_obj.id
    return file_obj
