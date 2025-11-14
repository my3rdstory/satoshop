from django.core.files.base import ContentFile
from django.utils import timezone
from fpdf import FPDF

from .contract_flow import FontConfig, resolve_contract_pdf_font
from .emails import send_contract_finalized_email


class ChatArchivePDF(FPDF):
    def __init__(self, font_config: FontConfig):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.font_config = font_config
        self.body_font = self._register_fonts(font_config)
        self.set_margins(15, 18, 15)
        self.set_auto_page_break(auto=True, margin=18)

    def _register_fonts(self, config: FontConfig) -> str:
        family = config.family or "Helvetica"
        if config.regular_path:
            self.add_font(family, "", str(config.regular_path), uni=True)
            bold_path = config.bold_path or config.regular_path
            self.add_font(family, "B", str(bold_path), uni=True)
        return family

    def footer(self):
        self.set_y(-15)
        self.set_font(self.body_font, "B", 9)
        text = f"-{self.page_no()}/{{nb}}-"
        self.cell(0, 10, text, 0, 0, "C")


def generate_chat_archive_pdf(contract):
    """FPDF 기반으로 계약 채팅 로그 PDF를 생성한다."""
    font_config = resolve_contract_pdf_font()
    pdf = ChatArchivePDF(font_config)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font(pdf.body_font, "", 11)
    line_height = 5

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
        pdf.multi_cell(0, line_height, line)

    messages = contract.messages.select_related("sender").order_by("created_at")
    if not messages.exists():
        pdf.multi_cell(0, line_height, "채팅 메시지가 존재하지 않습니다.")
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
            pdf.set_font(pdf.body_font, "B", 11)
            pdf.multi_cell(0, line_height, header)
            pdf.set_font(pdf.body_font, "", 11)
            for paragraph_line in message.content.splitlines() or [""]:
                pdf.multi_cell(0, line_height, f"  {paragraph_line}")
            pdf.ln(2)

    filename = f"contract-{contract.public_id}-chat.pdf"
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    contract.chat_archive.save(filename, ContentFile(pdf_bytes), save=False)
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
