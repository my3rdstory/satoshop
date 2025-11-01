import io
from django.core.files.base import ContentFile
from django.utils import timezone

from .emails import send_contract_finalized_email


def generate_chat_archive_pdf(contract):
    """
    계약 채팅 로그를 PDF로 생성해 계약에 첨부한다.

    ReportLab이 설치되어 있어야 하며, 설치되어 있지 않을 경우 RuntimeError를 발생시킨다.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("ReportLab 패키지가 설치되어 있어야 채팅 PDF를 생성할 수 있습니다.") from exc

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    text_object = pdf.beginText(margin, height - margin)
    text_object.setFont("Helvetica", 11)

    header_lines = [
        "SatoShop Expert - 계약 채팅 로그",
        f"계약 제목: {contract.title}",
        f"계약 ID: {contract.public_id}",
        f"생성자: {contract.created_by.get_full_name() or contract.created_by.username}",
        f"기록 생성일: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "※ 본 문서는 계약 채팅 내역을 보존하기 위한 용도로 자동 생성되었습니다.",
        "",
    ]

    for line in header_lines:
        text_object.textLine(line)

    messages = contract.messages.select_related("sender").order_by("created_at")
    if not messages.exists():
        text_object.textLine("채팅 메시지가 존재하지 않습니다.")
    else:
        for message in messages:
            timestamp = timezone.localtime(message.created_at).strftime("%Y-%m-%d %H:%M")
            sender = message.sender.get_full_name() if message.sender else "시스템"
            if not sender:
                sender = message.sender.username if message.sender else "시스템"
            role = message.get_sender_role_display() if message.sender_role else ""
            header = f"[{timestamp}] {sender}"
            if role:
                header += f" ({role})"
            text_object.textLine(header)

            for paragraph_line in message.content.splitlines() or [""]:
                text_object.textLine(f"  {paragraph_line}")
            text_object.textLine("")

            if text_object.getY() <= margin:
                pdf.drawText(text_object)
                pdf.showPage()
                text_object = pdf.beginText(margin, height - margin)
                text_object.setFont("Helvetica", 11)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    filename = f"contract-{contract.public_id}-chat.pdf"
    contract.chat_archive.save(filename, ContentFile(buffer.getvalue()), save=False)
    contract.archive_generated_at = timezone.now()
    contract.save(update_fields=["chat_archive", "archive_generated_at", "updated_at"])
    return contract.chat_archive


def finalize_contract(contract):
    """
    계약을 최종 확정하면서 채팅 PDF를 생성하고 이메일을 발송한다.
    """
    archive = generate_chat_archive_pdf(contract)
    send_contract_finalized_email(contract)
    return archive
