# subscriptions/admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import SubscriptionPlan, Subscription, Payment, PaymentCallback

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration', 'price', 'days', 'is_active', 'popular', 'subscriber_count')
    list_filter = ('duration', 'is_active', 'popular', 'created_at')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {'fields': ('name', 'description', 'features')}),
        ('Tarification', {'fields': ('duration', 'price', 'days')}),
        ('Options', {'fields': ('is_active', 'popular')}),
    )
    
    def subscriber_count(self, obj):
        return obj.subscriptions.count()
    subscriber_count.short_description = "Nombre d'abonnés"

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('reference', 'notchpay_reference', 'payment_method', 
                      'amount', 'status', 'transaction_date', 'created_at')
    can_delete = False
    show_change_link = True
    max_num = 5

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 
                   'is_currently_active', 'auto_renew', 'created_at')
    list_filter = ('status', 'auto_renew', 'plan', 'created_at')
    search_fields = ('user__username', 'user__email', 'plan__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PaymentInline]
    actions = ['mark_as_active', 'mark_as_expired', 'mark_as_cancelled']
    
    def is_currently_active(self, obj):
        if obj.is_active():
            return format_html('<span style="color:green;">✓</span>')
        return format_html('<span style="color:red;">✗</span>')
    is_currently_active.short_description = "Actif actuellement"
    
    def mark_as_active(self, request, queryset):
        queryset.update(status='ACTIVE')
    mark_as_active.short_description = "Marquer comme actif"
    
    def mark_as_expired(self, request, queryset):
        queryset.update(status='EXPIRED')
    mark_as_expired.short_description = "Marquer comme expiré"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
    mark_as_cancelled.short_description = "Marquer comme annulé"

class PaymentCallbackInline(admin.TabularInline):
    model = PaymentCallback
    extra = 0
    readonly_fields = ('raw_data', 'received_at')
    can_delete = False
    max_num = 5

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'amount', 'payment_method', 
                   'payment_type', 'status', 'transaction_date', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_type', 'created_at')
    search_fields = ('reference', 'notchpay_reference', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'authorization_url')
    inlines = [PaymentCallbackInline]
    actions = ['mark_as_success', 'mark_as_failed', 'mark_as_cancelled']
    
    def mark_as_success(self, request, queryset):
        queryset.update(status='SUCCESS', transaction_date=timezone.now())
    mark_as_success.short_description = "Marquer comme réussi"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='FAILED')
    mark_as_failed.short_description = "Marquer comme échoué"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
    mark_as_cancelled.short_description = "Marquer comme annulé"

@admin.register(PaymentCallback)
class PaymentCallbackAdmin(admin.ModelAdmin):
    list_display = ('payment', 'received_at')
    list_filter = ('received_at',)
    search_fields = ('payment__reference', 'payment__notchpay_reference', 'raw_data')
    date_hierarchy = 'received_at'
    readonly_fields = ('payment', 'raw_data', 'received_at')