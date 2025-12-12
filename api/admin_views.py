from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils.decorators import method_decorator
from django.views import View

from orders.models import Order
from lecture.models import LiveLectureOrder
from meetup.models import MeetupOrder
from file.models import FileOrder


@method_decorator(staff_member_required, name="dispatch")
class ChannelSalesView(View):
    template_name = "admin/api/channel_sales.html"

    def get(self, request):
        channel = request.GET.get("channel", "").strip()

        def base_filter(qs):
            return qs.filter(channel=channel) if channel else qs

        product_orders = base_filter(Order.objects.all())
        live_orders = base_filter(LiveLectureOrder.objects.all()) if hasattr(LiveLectureOrder, "channel") else []
        meetup_orders = base_filter(MeetupOrder.objects.all()) if hasattr(MeetupOrder, "channel") else []
        file_orders = base_filter(FileOrder.objects.all()) if hasattr(FileOrder, "channel") else []

        summary = []
        def add_summary(label, qs, amount_field="total_amount"):
            if not qs:
                return
            total = qs.aggregate(
                count=Count("id"),
                amount=Sum(amount_field),
            )
            summary.append({
                "label": label,
                "count": total.get("count") or 0,
                "amount": total.get("amount") or 0,
            })

        add_summary("상품 주문", product_orders, "total_amount")
        add_summary("라이브 강의", live_orders, "total_amount")
        add_summary("밋업", meetup_orders, "total_amount")
        add_summary("디지털 파일", file_orders, "total_amount")

        context = {
            "channel": channel,
            "product_orders": product_orders,
            "live_orders": live_orders,
            "meetup_orders": meetup_orders,
            "file_orders": file_orders,
            "summary": summary,
        }
        return render(request, self.template_name, context)
