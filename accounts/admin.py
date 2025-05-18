# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, UserPhoto, VerificationCode, SocialAccount

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'

class UserPhotoInline(admin.TabularInline):
    model = UserPhoto
    extra = 1
    max_num = 6

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Informations personnelles'), {'fields': ('email', 'phone_number', 'is_phone_verified', 
                                                  'first_name', 'last_name', 'date_of_birth', 
                                                  'gender', 'seeking', 'bio', 'location', 
                                                  'latitude', 'longitude')}),
        (_('Statut premium'), {'fields': ('is_premium', 'premium_until')}),
        (_('Vérification'), {'fields': ('is_verified', 'is_complete')}),
        (_('Autorisations'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Dates importantes'), {'fields': ('last_login', 'date_joined', 'last_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'phone_number', 'first_name', 'last_name', 
                   'is_premium', 'is_verified', 'is_staff', 'last_active')
    list_filter = ('is_premium', 'is_verified', 'is_staff', 'is_superuser', 'is_active', 'gender')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name', 'location')
    ordering = ('-date_joined',)
    readonly_fields = ('last_active',)
    inlines = (UserProfileInline, UserPhotoInline)

class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_id', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('user__username', 'user__email', 'provider_id')

class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'code')
    readonly_fields = ('created_at',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(SocialAccount, SocialAccountAdmin)
admin.site.register(VerificationCode, VerificationCodeAdmin)