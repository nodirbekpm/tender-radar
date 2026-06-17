"""Extend the User admin with an inline for per-user source visibility.

This is the main admin workflow from the spec: open a user, tick/untick which
sources they can see (e.g. grant the demo user 'B2B-Center').
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from apps.sources.models import UserSourcePermission


class UserSourcePermissionInline(admin.TabularInline):
    model = UserSourcePermission
    fk_name = "user"
    extra = 0
    autocomplete_fields = ("source",)
    verbose_name = "Source access"
    verbose_name_plural = "Source access (which marketplaces this user sees)"


class UserAdmin(DjangoUserAdmin):
    inlines = [UserSourcePermissionInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
