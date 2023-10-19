from modelcluster.models import ClusterableModel
from wagtail.core.fields import StreamField
from wagtail.snippets.models import register_snippet
from snap.apps.cms.blocks.menu import NavigationItem, FooterColumnsBlock
from wagtail.admin.edit_handlers import StreamFieldPanel


@register_snippet
class NavigationMenu(ClusterableModel):
    header_navigation = StreamField([("nav_items", NavigationItem())], blank=True)
    footer_navigation = StreamField(FooterColumnsBlock(max_num=4))

    panels: list = [
        StreamFieldPanel("header_navigation"),
        StreamFieldPanel("footer_navigation"),
    ]
