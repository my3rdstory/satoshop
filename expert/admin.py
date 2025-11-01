from django.contrib import admin, messages

from .models import Contract, ContractParticipant, ContractMessage, ContractEmailLog
from .services import generate_chat_archive_pdf


@admin.action(description="채팅 로그 PDF 생성")
def generate_chat_pdf(modeladmin, request, queryset):
    success_count = 0
    for contract in queryset:
        try:
            generate_chat_archive_pdf(contract)
            success_count += 1
        except RuntimeError as exc:
            messages.error(request, f"{contract.title}: {exc}")
        except Exception as exc:  # pylint: disable=broad-except
            messages.error(request, f"{contract.title}: 예기치 못한 오류 - {exc}")
    if success_count:
        messages.success(request, f"{success_count}건의 채팅 PDF를 생성했습니다.")


class ContractParticipantInline(admin.TabularInline):
    model = ContractParticipant
    extra = 0
    fields = ("user", "role", "lightning_identifier", "is_confirmed", "signed_at")
    readonly_fields = ("signed_at",)


class ContractMessageInline(admin.TabularInline):
    model = ContractMessage
    extra = 0
    fields = ("created_at", "sender", "sender_role", "message_type", "content")
    readonly_fields = ("created_at", "sender", "sender_role", "message_type", "content")
    can_delete = False


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "created_by__username")
    readonly_fields = ("public_id", "created_at", "updated_at", "archive_generated_at")
    inlines = [ContractParticipantInline, ContractMessageInline]
    actions = [generate_chat_pdf]


@admin.register(ContractEmailLog)
class ContractEmailLogAdmin(admin.ModelAdmin):
    list_display = ("contract", "subject", "sent_at", "success")
    list_filter = ("success", "sent_at")
    search_fields = ("contract__title", "subject", "recipients")
    readonly_fields = ("contract", "recipients", "subject", "message", "sent_at", "success", "error_message")
