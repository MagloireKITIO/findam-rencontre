# matchmaking/admin.py

from django.contrib import admin
from .models import (
    Like, Dislike, Match, BlockedUser, 
    SwipeAction, UserPreference, Report
)

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('liker', 'liked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('liker__username', 'liker__email', 'liked__username', 'liked__email')
    date_hierarchy = 'created_at'

@admin.register(Dislike)
class DislikeAdmin(admin.ModelAdmin):
    list_display = ('disliker', 'disliked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('disliker__username', 'disliker__email', 'disliked__username', 'disliked__email')
    date_hierarchy = 'created_at'

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'created_at', 'is_active')
    list_filter = ('created_at', 'is_active')
    search_fields = ('user1__username', 'user1__email', 'user2__username', 'user2__email')
    date_hierarchy = 'created_at'
    actions = ['deactivate_matches', 'activate_matches']
    
    def deactivate_matches(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_matches.short_description = "Désactiver les matchs sélectionnés"
    
    def activate_matches(self, request, queryset):
        queryset.update(is_active=True)
    activate_matches.short_description = "Activer les matchs sélectionnés"

@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocker__email', 'blocked__username', 'blocked__email', 'reason')
    date_hierarchy = 'created_at'

@admin.register(SwipeAction)
class SwipeActionAdmin(admin.ModelAdmin):
    list_display = ('user', 'target', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'user__email', 'target__username', 'target__email')
    date_hierarchy = 'created_at'

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'min_age', 'max_age', 'distance', 'show_verified_only', 'updated_at')
    list_filter = ('show_verified_only', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'updated_at'

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported', 'reason', 'is_reviewed', 'is_valid', 'created_at')
    list_filter = ('reason', 'is_reviewed', 'is_valid', 'created_at')
    search_fields = ('reporter__username', 'reporter__email', 'reported__username', 'reported__email', 'details')
    date_hierarchy = 'created_at'
    actions = ['mark_as_reviewed', 'mark_as_valid', 'mark_as_invalid']
    
    def mark_as_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)
    mark_as_reviewed.short_description = "Marquer comme examiné"
    
    def mark_as_valid(self, request, queryset):
        queryset.update(is_reviewed=True, is_valid=True)
    mark_as_valid.short_description = "Marquer comme examiné et valide"
    
    def mark_as_invalid(self, request, queryset):
        queryset.update(is_reviewed=True, is_valid=False)
    mark_as_invalid.short_description = "Marquer comme examiné et invalide"