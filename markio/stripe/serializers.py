from django.db.models import Count
from django.utils.functional import cached_property
from oscar.core.loading import get_class, get_model
from oscarapi.serializers import checkout, product

from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import APIException

from snap.apps.catalogue import utils as catalogue_utils
from snap.apps.catalogue.models import Product
from snap.utils import (
    absolute_product_url,
    absolute_dashboard_product_url,
    find_value_type,
)

import json


class TotalReviewBarSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    count = serializers.IntegerField()
    percentage = serializers.IntegerField()

    class Meta:
        fields = "__all__"


class ProductSerializer(product.ProductSerializer):
    price = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField("get_variants")
    reviews = ProductReviewSerializer(many=True, required=False)
    top_review = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    total_reviews_bar = serializers.SerializerMethodField()
    vendor_id = serializers.CharField(required=True)
    vendor_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    dashboard_url = serializers.SerializerMethodField()
    delete_images_pk = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "url",
            "dashboard_url",
            "id",
            "title",
            "description",
            "images",
            "price",
            "vendor_id",
            "vendor_name",
            "attributes",
            "reviews",
            "top_review",
            "total_reviews",
            "total_reviews_bar",
            "image",
            "status",
            "delete_images_pk",
            "category",
            "slug",
        ]
        read_only_fields = ["reviews"]


    def get_vendor_name(self, instance):
        try:
            return instance.vendor.user.username
        except Exception:
            None

    def get_url(self, instance):
        return absolute_product_url(instance)

    def get_dashboard_url(self, instance):
        return absolute_dashboard_product_url(instance.pk)

    def get_price(self, instance):
        request = self.context.get("request")
        strategy = Selector().strategy(request=request, user=request.user)

        ser = checkout.PriceSerializer(
            strategy.fetch_for_product(instance).price, context={"request": request}
        )
        return ser.data

    @staticmethod
    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            "reviews",
            "product_class",
            "images",
            "stockrecords",
            "attributes",
            "categories",
            "attribute_values",
        )
        return queryset

    def get_variants(self, instance):
        variants = []
        if instance.is_parent:
            for variant in instance.children.all():
                variants.append(variant.to_dict)
        if instance.is_child:
            variants.append(instance.parent.to_dict)
            for sibling in instance.parent.children.exclude(id=instance.id):
                variants.append(sibling.to_dict)
        serializer = ProductVariantSerializer(variants, many=True)
        return serializer.data

    def get_top_review(self, obj):
        if obj.reviews.exists():
            top_review = obj.reviews.order_by("-delta_votes")[0]
            serializer = ProductReviewSerializer(top_review)
            return serializer.data
        return None

    def get_total_reviews(self, instance):
        return instance.reviews.all().count()

    def get_total_reviews_bar(self, instance):
        if instance.reviews.exists():
            total_reviews = instance.reviews.count()
            divide_by = 100 / total_reviews
            scores = []
            seen = []
            for score_item in (
                instance.reviews.values("score")
                .order_by("score")
                .annotate(count=Count("score"))
            ):
                percentage = score_item.get("count") * divide_by
                score_item.update({"percentage": percentage})
                scores.append(score_item)
                seen.append(score_item.get("score"))
            for number in range(1, 6):
                if number not in seen:
                    scores.append({"score": number, "count": 0, "percentage": 0})
            serializer = TotalReviewBarSerializer(
                sorted(scores, key=lambda k: k["score"], reverse=True), many=True
            )
            return serializer.data
        return None

    def get_image(self, instance):
        if instance.images.exists():
            image = instance.images.first()
            return {
                "url": image.original.url,
                "alt_text": image.alt_text,
                "id": image.pk,
            }
        return None

    def get_images(self, instance):
        if instance.images.exists():
            images = []
            for image in instance.images.all():
                images.append(
                    {
                        "url": image.original.url,
                        "alt_text": image.alt_text,
                        "id": image.pk,
                    }
                )
            return images
        return None

    def get_status(self, instance):
        if instance.is_public:
            return "live"
        return "draft"

    def get_delete_images_pk(self, instance):
        return []

    def get_category(self, instance):
        if instance.categories.exists():
            return instance.categories.first().name
        return None
