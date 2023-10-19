from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter, OrderingFilter

from influencer.apps.marketing.models import Campaign
from influencer.apps.users.models import User
from influencer.apps.marketing.serializers import CampaignSerializer
from influencer.apps.marketing.pagination import StandardResultsSetPagination
4

class CampaignListApiView(ListAPIView):    
    serializer_class = CampaignSerializer
    pagination_class = StandardResultsSetPagination
    search_fields = ["name"]
    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]
    def get_queryset(self):
        if self.request.headers.get("Authorization"):
            user = User.objects.get(auth_token=self.request.headers.get("Authorization"))
        else:
            user = self.request.user
        return Campaign.objects.filter(user=user).order_by('id')

    def post(self, request):
        if self.request.headers.get("Authorization"):
            user = User.objects.get(auth_token=self.request.headers.get("Authorization"))
        else:
            user = self.request.user
        if user:
            if not request.data.get("id"):
                serializer = CampaignSerializer(data=request.data, context={"request" : request, "user": user})
                if serializer.is_valid():
                    campaign = serializer.create(validated_data=serializer.validated_data)
                    campaign.save()
                    return Response(CampaignSerializer(campaign).data)
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"msg": "Something went wrong!"})
            else:
                campaign_obj = Campaign.objects.get(id=request.data.get("id"))
                if campaign_obj:
                    serializer = CampaignSerializer(data=request.data, context={"request" : request, "user": user})
                    if serializer.is_valid():
                        campaign = serializer.update(campaign_obj, validated_data=serializer.validated_data)
                        return Response(CampaignSerializer(campaign).data)
                    return Response(
                            status=status.HTTP_400_BAD_REQUEST,
                            data={"msg": "Something went wrong!"})
