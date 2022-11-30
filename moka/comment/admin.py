from comment.models import Comment, LikeComment
from django.contrib import admin


class CommentAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "commenter",
        "episode",
        "parent",
    )
    list_display = (
        "owner_name",
        "episode_title",
        "created_at",
    )
    search_fields = ("commenter__display_name", "episode__title")
    sortable_by = ("created_at",)
    actions = None

    @admin.display()
    def owner_name(self, obj: Comment):
        return obj.commenter.display_name

    @admin.display()
    def episode_title(self, obj: Comment):
        return obj.episode.title


admin.site.register(Comment, CommentAdmin)


class LikeCommentAdmin(admin.ModelAdmin):
    list_display = (
        "owner_name",
        "episode_title",
    )
    search_fields = ("liker__display_name", "comment__episode__title")
    actions = None

    @admin.display()
    def owner_name(self, obj: LikeComment):
        return obj.liker.display_name

    @admin.display()
    def episode_title(self, obj: LikeComment):
        return obj.comment.episode.title


admin.site.register(LikeComment, LikeCommentAdmin)
