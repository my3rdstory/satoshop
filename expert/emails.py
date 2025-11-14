
import logging
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

from myshop.models import SiteSettings

from .models import ContractEmailLog
from .contract_flow import render_contract_pdf

logger = logging.getLogger(__name__)


def send_contract_finalized_email(contract, additional_recipients=None, attachments=None):
    """
    계약 확정 시 이메일과 채팅 PDF를 첨부해 발송한다.

    SiteSettings에 Expert Gmail 설정이 없을 경우 RuntimeError를 발생시킨다.
    """
    site_settings = SiteSettings.get_settings()
    email_config = site_settings.get_expert_email_settings()
    if not email_config:
        raise RuntimeError("Expert Gmail 설정이 필요합니다. 어드민에서 Gmail 주소와 앱 비밀번호를 입력해주세요.")

    recipients = [
        participant.user.email
        for participant in contract.participants.select_related("user")
        if participant.user.email
    ]
    if additional_recipients:
        recipients.extend(additional_recipients)

    recipients = sorted(set(filter(None, recipients)))
    if not recipients:
        raise RuntimeError("계약 참여자에게 등록된 이메일 주소가 없습니다.")

    subject = f"[SatoShop Expert] 계약 완료 안내 - {contract.title}"
    context = {
        "contract": contract,
        "site_settings": site_settings,
        "generated_at": timezone.localtime(timezone.now()),
    }
    body = render_to_string("expert/emails/contract_finalized.txt", context)

    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host='smtp.gmail.com',
        port=587,
        username=email_config["address"],
        password=email_config["app_password"],
        use_tls=True,
    )

    sender = f"{email_config['sender_name']} <{email_config['address']}>" if email_config["sender_name"] else email_config["address"]
    email_message = EmailMessage(
        subject=subject,
        body=body,
        from_email=sender,
        to=recipients,
        connection=connection,
    )

    if contract.chat_archive:
        email_message.attach_file(contract.chat_archive.path)

    if attachments:
        for attachment in attachments:
            if isinstance(attachment, str):
                email_message.attach_file(attachment)
            elif isinstance(attachment, tuple) and len(attachment) == 3:
                email_message.attach(*attachment)

    success = True
    error_message = ""
    try:
        email_message.send(fail_silently=False)
    except Exception as exc:  # pylint: disable=broad-except
        success = False
        error_message = str(exc)
        raise
    finally:
        ContractEmailLog.objects.create(
            contract=contract,
            recipients=", ".join(recipients),
            subject=subject,
            message=body,
            success=success,
            error_message=error_message,
        )


def send_direct_contract_document_email(document, attachment=None):
    """직접 계약 플로우에서 계약서를 이메일로 전송하고 결과를 반환."""

    site_settings = SiteSettings.get_settings()
    email_config = site_settings.get_expert_email_settings()
    subject = f"[SatoShop Expert] 계약서가 완료되었습니다 - {document.payload.get('title', '-') }"
    context = {
        "document": document,
        "generated_at": timezone.localtime(timezone.now()),
    }
    body = render_to_string("expert/emails/direct_contract_finalized.txt", context)
    pdf_binary = None
    pdf_name = None
    if attachment and len(attachment) == 2:
        pdf_name, pdf_binary = attachment
    elif document.final_pdf:
        try:
            document.final_pdf.open("rb")
            try:
                pdf_binary = document.final_pdf.read()
            finally:
                document.final_pdf.close()
            if document.final_pdf.name:
                pdf_name = document.final_pdf.name.split("/")[-1] or None
        except Exception as exc:
            logger.warning("최종 계약서 PDF를 스토리지에서 읽다가 실패했습니다: %s", exc)
            pdf_binary = None
            pdf_name = None

    if pdf_binary is None:
        try:
            contract_body = ((document.payload or {}).get("contract_template") or {}).get("content") or ""
            regenerated = render_contract_pdf(document, contract_body)
            pdf_binary = regenerated.read()
            pdf_name = regenerated.name or None
        except Exception as exc:  # pragma: no cover - best effort fallback
            logger.error("최종 계약서 PDF 재생성 실패: %s", exc)
            pdf_binary = None
            pdf_name = None

    if pdf_binary is not None and not pdf_name:
        pdf_name = f"{document.slug}.pdf"
    statuses = {}
    gmail_warning = "Expert Gmail 설정이 필요합니다. 어드민에서 Gmail 주소와 앱 비밀번호를 입력해 주세요."

    connection = None
    sender = None
    if email_config:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host='smtp.gmail.com',
            port=587,
            username=email_config["address"],
            password=email_config["app_password"],
            use_tls=True,
        )
        sender = (
            f"{email_config['sender_name']} <{email_config['address']}>"
            if email_config.get("sender_name")
            else email_config["address"]
        )

    for key, email in {"creator": document.creator_email, "counterparty": document.counterparty_email}.items():
        status = {"email": email or "", "sent": False, "message": ""}
        if not email:
            status["message"] = "이메일이 입력되지 않았습니다."
            statuses[key] = status
            continue
        if not email_config or not sender:
            status["message"] = gmail_warning
            statuses[key] = status
            continue
        email_message = EmailMessage(
            subject=subject,
            body=body,
            from_email=sender,
            to=[email],
            connection=connection,
        )
        if pdf_binary and pdf_name:
            email_message.attach(pdf_name, pdf_binary, "application/pdf")
        try:
            email_message.send(fail_silently=False)
            status["sent"] = True
        except Exception as exc:  # pylint: disable=broad-except
            status["message"] = str(exc)
        statuses[key] = status
    return statuses
