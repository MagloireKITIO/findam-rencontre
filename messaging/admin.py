# messaging/admin.py

from django.contrib import admin
from .models import Conversation, Message, MessageReceipt, DeletedMessage

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'content', 'message_type', 'attachment', 'is_read', 'created_at')
    can_delete = False
    show_change_link = True

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_participants', 'message_count', 'created_at', 'updated_at', 'is_active')
    list_filter = ('created_at', 'updated_at', 'is_active')
    search_fields = ('participants__username', 'participants__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    filter_horizontal = ('participants',)
    date_hierarchy = 'created_at'
    
    def display_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    display_participants.short_description = "Participants"
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Nombre de messages"
    
    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'truncated_content', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('content', 'sender__username', 'sender__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def truncated_content(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    truncated_content.short_description = "Contenu"

@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'recipient', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('message__content', 'recipient__username', 'recipient__email')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

@admin.register(DeletedMessage)
class DeletedMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'deleted_at')
    list_filter = ('deleted_at',)
    search_fields = ('message__content', 'user__username', 'user__email')
    readonly_fields = ('deleted_at',)
    date_hierarchy = 'deleted_at'