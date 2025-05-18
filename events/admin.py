# events/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import EventCategory, Event, EventParticipant, EventComment, EventSavedByUser

class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 0
    readonly_fields = ('registration_date',)

class EventCommentInline(admin.TabularInline):
    model = EventComment
    extra = 0
    readonly_fields = ('user', 'created_at')
    can_delete = False
    show_change_link = True

@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'event_count')
    search_fields = ('name',)
    
    def event_count(self, obj):
        return obj.events.count()
    event_count.short_description = "Nombre d'événements"

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'location_name', 'city', 'start_date', 
                   'status', 'is_free', 'price_display', 'participant_count', 'created_by')
    list_filter = ('status', 'category', 'city', 'is_free', 'registration_required')
    search_fields = ('title', 'description', 'location_name', 'address', 'city')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at', 'participant_count', 'image_preview')
    inlines = [EventParticipantInline, EventCommentInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'description', 'category', 'image', 'image_preview')
        }),
        ('Lieu', {
            'fields': ('location_name', 'address', 'city', 'latitude', 'longitude')
        }),
        ('Date et heure', {
            'fields': ('start_date', 'end_date')
        }),
        ('Participants', {
            'fields': ('is_free', 'price', 'max_participants', 'registration_required', 
                     'registration_deadline', 'participant_count')
        }),
        ('Statut', {
            'fields': ('status', 'created_by', 'created_at', 'updated_at')
        }),
    )
    
    def price_display(self, obj):
        if obj.is_free:
            return "Gratuit"
        elif obj.price:
            return f"{obj.price} FCFA"
        return "-"
    price_display.short_description = "Prix"
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = "Nombre de participants"
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 150px; max-width: 300px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = "Aperçu de l'image"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si c'est une nouvelle création
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'status', 'registration_date')
    list_filter = ('status', 'registration_date', 'event')
    search_fields = ('user__username', 'user__email', 'event__title')
    date_hierarchy = 'registration_date'
    readonly_fields = ('registration_date',)

@admin.register(EventComment)
class EventCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'truncated_content', 'created_at')
    list_filter = ('created_at', 'event')
    search_fields = ('user__username', 'user__email', 'event__title', 'content')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    def truncated_content(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    truncated_content.short_description = "Commentaire"

@admin.register(EventSavedByUser)
class EventSavedByUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__username', 'user__email', 'event__title')
    date_hierarchy = 'saved_at'
    readonly_fields = ('saved_at',)