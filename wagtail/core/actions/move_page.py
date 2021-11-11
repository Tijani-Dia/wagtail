import logging

from django.db import transaction

from wagtail.core.log_actions import log
from wagtail.core.signals import post_page_move, pre_page_move


logger = logging.getLogger("wagtail.core")


def move_page(page, target, pos, user):
    from wagtail.core.models import Page

    # Determine old and new parents
    parent_before = page.get_parent()
    if pos in ("first-child", "last-child", "sorted-child"):
        parent_after = target
    else:
        parent_after = target.get_parent()

    # Determine old and new url_paths
    # Fetching new object to avoid affecting `page`
    old_page = Page.objects.get(id=page.id)
    old_url_path = old_page.url_path
    new_url_path = old_page.set_url_path(parent=parent_after)

    # Emit pre_page_move signal
    pre_page_move.send(
        sender=page.specific_class or page.__class__,
        instance=page,
        parent_page_before=parent_before,
        parent_page_after=parent_after,
        url_path_before=old_url_path,
        url_path_after=new_url_path,
    )

    # Only commit when all descendants are properly updated
    with transaction.atomic():
        # Allow treebeard to update `path` values
        super(Page, page).move(target, pos=pos)

        # Treebeard's move method doesn't actually update the in-memory instance,
        # so we need to work with a freshly loaded one now
        new_page = Page.objects.get(id=page.id)
        new_page.url_path = new_url_path
        new_page.save()

        # Update descendant paths if url_path has changed
        if old_url_path != new_url_path:
            new_page._update_descendant_url_paths(old_url_path, new_url_path)

    # Emit post_page_move signal
    post_page_move.send(
        sender=page.specific_class or page.__class__,
        instance=new_page,
        parent_page_before=parent_before,
        parent_page_after=parent_after,
        url_path_before=old_url_path,
        url_path_after=new_url_path,
    )

    # Log
    log(
        instance=page,
        # Check if page was reordered (reordering doesn't change the parent)
        action="wagtail.reorder" if parent_before.id == target.id else "wagtail.move",
        user=user,
        data={
            "source": {
                "id": parent_before.id,
                "title": parent_before.specific_deferred.get_admin_display_title(),
            },
            "destination": {
                "id": parent_after.id,
                "title": parent_after.specific_deferred.get_admin_display_title(),
            },
        },
    )
    logger.info('Page moved: "%s" id=%d path=%s', page.title, page.id, new_url_path)
