from django.contrib import admin
from django.db.models import Q


class HasParticipantsFilter(admin.SimpleListFilter):
    """참가자 유무 필터"""
    title = '참가자 유무'
    parameter_name = 'has_participants'

    def lookups(self, request, model_admin):
        return (
            ('yes', '참가자 있음'),
            ('no', '참가자 없음'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(orders__status__in=['confirmed', 'completed']).distinct()
        if self.value() == 'no':
            return queryset.exclude(orders__status__in=['confirmed', 'completed']).distinct()


class PaymentHashFilter(admin.SimpleListFilter):
    """결제해시 유무 필터"""
    title = '결제해시 유무'
    parameter_name = 'payment_hash_exists'

    def lookups(self, request, model_admin):
        return (
            ('yes', '결제해시 있음'),
            ('no', '결제해시 없음'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(payment_hash__isnull=True).exclude(payment_hash='')
        if self.value() == 'no':
            return queryset.filter(Q(payment_hash__isnull=True) | Q(payment_hash=''))


class HasPendingOrdersFilter(admin.SimpleListFilter):
    """미결제 주문 유무 필터"""
    title = '미결제 주문 유무'
    parameter_name = 'has_pending_orders'

    def lookups(self, request, model_admin):
        return (
            ('yes', '있음'),
            ('no', '없음'),
        )

    def queryset(self, request, queryset):
        from ..models import MeetupOrder
        if self.value() == 'yes':
            user_ids_with_pending = MeetupOrder.objects.filter(
                status='pending'
            ).values_list('user_id', flat=True).distinct()
            return queryset.filter(id__in=user_ids_with_pending)
        if self.value() == 'no':
            user_ids_with_pending = MeetupOrder.objects.filter(
                status='pending'
            ).values_list('user_id', flat=True).distinct()
            return queryset.exclude(id__in=user_ids_with_pending)


class HasAttendedMeetupsFilter(admin.SimpleListFilter):
    """실제 참석 유무 필터"""
    title = '실제 참석 유무'
    parameter_name = 'has_attended_meetups'

    def lookups(self, request, model_admin):
        return (
            ('yes', '있음'),
            ('no', '없음'),
        )

    def queryset(self, request, queryset):
        from ..models import MeetupOrder
        if self.value() == 'yes':
            user_ids_attended = MeetupOrder.objects.filter(
                status__in=['confirmed', 'completed'],
                attended=True
            ).values_list('user_id', flat=True).distinct()
            return queryset.filter(id__in=user_ids_attended)
        if self.value() == 'no':
            user_ids_attended = MeetupOrder.objects.filter(
                status__in=['confirmed', 'completed'],
                attended=True
            ).values_list('user_id', flat=True).distinct()
            return queryset.exclude(id__in=user_ids_attended) 