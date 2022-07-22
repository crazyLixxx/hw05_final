from django.contrib import admin

from .models import Comment, Group, Post


class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'author', 'post', 'text')
    list_filter = ('post', 'author',)
    search_fields = ('text',)
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    list_display = ('pk', 'slug', 'title', 'description')
    search_fields = ('slug', 'title',)
    list_filter = ('title',)
    empty_value_display = '-пусто-'


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'created', 'author', 'group', 'text')
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('created',)
    empty_value_display = '-пусто-'


admin.site.register(Group, GroupAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
