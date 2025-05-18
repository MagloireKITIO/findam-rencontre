# notifications/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationPreference, DeviceToken

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'context_type', 'title_truncated', 
                   'is_read', 'is_email_sent', 'is_push_sent', 'created_at')
    list_filter = ('notification_type', 'context_type', 'is_read', 'is_email_sent', 
                  'is_push_sent', 'created_at')
    search_fields = ('recipient__username', 'recipient__email', 'title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_read', 'mark_as_unread']
    
    def title_truncated(self, obj):
        if len(obj.title) > 50:
            return obj.title[:50] + "..."
        return obj.title
    title_truncated.short_description = "Titre"
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Marquer comme non lu"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'receive_email', 'receive_push', 'matches', 'messages', 
                   'likes', 'events', 'subscription', 'system')
    list_filter = ('receive_email', 'receive_push', 'matches', 'messages', 
                  'likes', 'events', 'subscription', 'system')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['enable_all', 'disable_all']
    
    def enable_all(self, request, queryset):
        queryset.update(
            receive_email=True, 
            receive_push=True, 
            matches=True, 
            messages=True,
            likes=True, 
            events=True, 
            subscription=True, 
            system=True
        )
    enable_all.short_description = "Activer toutes les notifications"
    
    def disable_all(self, request, queryset):
        queryset.update(
            receive_email=False, 
            receive_push=False, 
            matches=False, 
            messages=False,
            likes=False, 
            events=False, 
            subscription=False, 
            system=False
        )
    disable_all.short_description = "Désactiver toutes les notifications"

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'device_name', 'token_truncated', 'is_active', 'created_at', 'last_used')
    list_filter = ('platform', 'is_active', 'created_at', 'last_used')
    search_fields = ('user__username', 'user__email', 'device_name', 'token')
    readonly_fields = ('created_at', 'last_used')
    actions = ['deactivate_tokens', 'activate_tokens']
    
    def token_truncated(self, obj):
        if len(obj.token) > 20:
            return obj.token[:20] + "..."
        return obj.token
    token_truncated.short_description = "Token"
    
    def deactivate_tokens(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_tokens.short_description = "Désactiver les tokens"
    
    def activate_tokens(self, request, queryset):
        queryset.update(is_active=True)
    activate_tokens.short_description = "Activer les tokens"