from django.contrib.auth.models import User
from django.db.models import Count, F
from django.db.models.functions import TruncDate, Floor
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jcourse_api.models import Announcement, Review, Course
from jcourse_api.serializers import AnnouncementSerializer


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Announcement.objects.filter(available=True)
    serializer_class = AnnouncementSerializer
    pagination_class = None


class StatisticView(APIView):

    @method_decorator(cache_page(60))
    def get(self, request: Request):
        user_join_time = User.objects.values(date=TruncDate("date_joined")).annotate(
            count=Count("id")).order_by("date")
        review_create_time = Review.objects.values(date=TruncDate("created_at")).annotate(
            count=Count("id")).order_by("date")
        course_review_count_dist = Course.objects.filter(review_count__gt=0).values(value=F("review_count")).annotate(
            count=Count("value")).order_by("value")
        course_review_avg_dist = Course.objects.filter(review_avg__gt=0).values(value=Floor("review_avg")).annotate(
            count=Count("value")).order_by("value")
        review_rating_dist = Review.objects.values(value=F("rating")).annotate(
            count=Count("value")).order_by("value")
        return Response({'course_count': Course.objects.count(),
                         'course_with_review_count': Course.objects.filter(review_count__gt=0).count(),
                         'user_count': User.objects.count(),
                         'review_count': Review.objects.count(),
                         'user_join_time': user_join_time,
                         'review_create_time': review_create_time,
                         'course_review_count_dist': course_review_count_dist,
                         'course_review_avg_dist': course_review_avg_dist,
                         'review_rating_dist': review_rating_dist
                         },
                        status=status.HTTP_200_OK)
