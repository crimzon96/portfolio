from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import (FieldPanel, FieldRowPanel,
                                         InlinePanel, MultiFieldPanel,
                                         StreamFieldPanel)
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Page, PageManager
from wagtail.search.queryset import SearchableQuerySetMixin

from snap.apps.cms.blocks import hero, web


class PageQuerySet(SearchableQuerySetMixin, models.QuerySet):
    def live(self):
        return self.filter(live=True)


class CustomPageManager(PageManager):
    """ Turn all querysets in PageQuerySet """

    def get_queryset(self):
        return PageQuerySet(self.model, using=self._db)  # Important!


class BasePage(Page):
    ROBOT_CHOICES = [
        ("index, follow", "index, follow"),
        ("index, nofollow", "index, nofollow"),
        ("noindex, follow", "noindex, follow"),
        ("noindex, nofollow", "noindex, nofollow"),
    ]
    seo_keywords = models.CharField(
        "seo keywords", max_length=250, null=True, blank=True
    )
    seo_robots = models.CharField(
        "seo robots",
        choices=ROBOT_CHOICES,
        default=ROBOT_CHOICES[0][0],
        max_length=50,
        null=True,
        blank=True,
    )

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
                FieldPanel("seo_keywords"),
                FieldPanel("seo_robots"),
            ],
            "Common page configuration",
        )
    ]

    class Meta:
        abstract = True

    objects = CustomPageManager()


BODY_CHILDREN = [
    ("featured_users", web.FeaturedUsersBlock()),
    ("find_button_with_six_fields", web.FindButtonWithSixFieldsBlock()),
    ("text_alignment", web.TextAlignmentBlock()),
    ("two_columns", web.TwoColumnBlock()),
    ("multi_item_carousel", web.MultiItemCarouselBlock()),
    ("cta_hover_button", web.CTAHoverButtonBlock()),
    ("text_three_icons", web.TextThreeIconsBlock()),
    ("faq", web.FAQBlock()),
]


class HomePage(BasePage):
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["ContentPage", "ContactPage", "SupportListPage"]
    header = StreamField(hero.HeroStreamBlock(max_num=1), default=[])
    header_bottom = StreamField(
        [("header_bottom", web.HeaderBottomCTABlock())], default=[]
    )
    body = StreamField(BODY_CHILDREN, default=None)
    content_panels = BasePage.content_panels + [
        StreamFieldPanel("header", heading="Header", classname="collapsible collapsed"),
        StreamFieldPanel(
            "header_bottom", heading="Header bottom", classname="collapsible collapsed"
        ),
        StreamFieldPanel("body", heading="bodu", classname="collapsible collapsed"),
    ]

    objects = CustomPageManager()

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        return context


class ContentPage(BasePage):
    parent_page_types = ["HomePage"]
    header = StreamField(hero.HeroStreamBlock(max_num=1), default=[], blank=True)
    body = StreamField(BODY_CHILDREN, default=None)
    content_panels = BasePage.content_panels + [
        StreamFieldPanel("header", heading="Header", classname="collapsible collapsed"),
        StreamFieldPanel("body", heading="body", classname="collapsible collapsed"),
    ]

    objects = CustomPageManager()

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        return context


class FormField(AbstractFormField):
    page = ParentalKey("ContactPage", related_name="custom_form_fields")


class ContactPage(AbstractEmailForm):
    parent_page_types = ["HomePage"]
    thank_you_text = RichTextField(blank=True)
    header = StreamField(hero.HeroStreamBlock(max_num=1), default=[], blank=True)
    body = StreamField([("support", web.SupportBlock())], default=None)
    content_panels = (
        AbstractEmailForm.content_panels
        + [
            StreamFieldPanel(
                "header", heading="Header", classname="collapsible collapsed"
            ),
            StreamFieldPanel("body"),
        ]
        + [
            InlinePanel("custom_form_fields", label="Form fields"),
            FieldPanel("thank_you_text", classname="full"),
            MultiFieldPanel(
                [
                    FieldRowPanel(
                        [
                            FieldPanel("from_address", classname="col6"),
                            FieldPanel("to_address", classname="col6"),
                        ]
                    ),
                    FieldPanel("subject"),
                ],
                "Email Notification Config",
            ),
        ]
    )

    def get_form_fields(self):
        return self.custom_form_fields.all()


class SupportListPage(BasePage):
    parent_page_types = ["ContactPage"]
    subpage_types = ["SupportPage"]
    header = StreamField(hero.HeroStreamBlock(max_num=1), default=[], blank=True)
    content_panels = BasePage.content_panels + [
        StreamFieldPanel("header", heading="Header", classname="collapsible collapsed"),
    ]

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        context["children"] = self.get_children()
        return context


class SupportPage(BasePage):
    parent_page_types = ["SupportListPage"]
    header = StreamField(hero.HeroStreamBlock(max_num=1), default=[], blank=True)
    text = models.TextField(null=True)
    body = RichTextField()
    content_panels = BasePage.content_panels + [
        StreamFieldPanel("header", heading="Header", classname="collapsible collapsed"),
        FieldPanel("text"),
        FieldPanel("body"),
    ]

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        context["parent_page"] = self.get_parent()
        return context
