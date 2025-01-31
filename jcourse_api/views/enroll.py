from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from jcourse_api.models import *
from jcourse_api.serializers import CourseListSerializer
from jcourse_api.views.course import get_course_list_queryset
from oauth.utils import jaccount


def parse_jaccount_courses(response: dict):
    codes = []
    teachers = []
    for entity in response['entities']:
        codes.append(entity['course']['code'])
        teachers.append(entity['teachers'][0]['name'])
    return codes, teachers


def find_exist_course_ids(codes: list, teachers: list):
    former_codes = FormerCode.objects.filter(old_code__in=codes).values('old_code', 'new_code')
    former_codes_dict = {}
    for former_code in former_codes:
        former_codes_dict[former_code['old_code']] = former_code['new_code']
    conditions = Q(pk=None)
    for code, teacher in zip(codes, teachers):
        if former_codes_dict.get(code, None):
            conditions = conditions | (
                    (Q(code=former_codes_dict[code]) | Q(code=code)) & Q(main_teacher__name=teacher))
        else:
            conditions = conditions | (Q(code=code) & Q(main_teacher__name=teacher))
    return Course.objects.filter(conditions).values_list('id', flat=True)


def sync_enroll_course(user: User, course_ids: list, term: str):
    try:
        semester = Semester.objects.get(name=term)
    except Semester.DoesNotExist:
        semester = None
    enroll_courses = []
    for course_id in course_ids:
        enroll_courses.append(EnrollCourse(user=user, course_id=course_id, semester=semester))
    # remove withdrawn courses
    EnrollCourse.objects.filter(user=user, semester=semester).exclude(course_id__in=course_ids).delete()
    EnrollCourse.objects.bulk_create(enroll_courses, ignore_conflicts=True)


def get_jaccount_lessons(token: dict, term: str):
    return jaccount.get(f'v1/me/lessons/{term}/', token=token, params={"classes": False}).json()


@api_view(['POST'])
def sync_lessons(request: Request, term: str = '2018-2019-2'):
    token = request.session.get('token', None)
    if token is None:
        return Response({'detail': '未授权获取课表信息'}, status=status.HTTP_401_UNAUTHORIZED)
    resp = get_jaccount_lessons(token, term)
    if resp['errno'] == 0:
        codes, teachers = parse_jaccount_courses(resp)
        existed_courses_ids = find_exist_course_ids(codes, teachers)
        sync_enroll_course(request.user, existed_courses_ids, term)

    courses = get_course_list_queryset(request.user)
    courses = courses.filter(enrollcourse__user=request.user)
    serializer = CourseListSerializer(courses, many=True)
    return Response(serializer.data)


class EnrollCourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseListSerializer
    pagination_class = None

    def get_queryset(self):
        courses = get_course_list_queryset(self.request.user)
        return courses.filter(enrollcourse__user=self.request.user)
