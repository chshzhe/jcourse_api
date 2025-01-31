from io import StringIO

from django.contrib.auth.models import User
from django.test import TestCase

from jcourse_api.models import Semester
from jcourse_api.tests import create_test_env, create_review
from jcourse_api.utils import *


class MergeTest(TestCase):
    def setUp(self) -> None:
        create_test_env()
        self.user = User.objects.get(username='test')
        self.old_review = create_review('test', 'CS1500', 3)
        self.old_course = Course.objects.get(code='CS1500')
        self.old_teacher = Teacher.objects.get(tid=1, name='高女士')
        self.semester = Semester.objects.get(name='2021-2022-1')
        self.enroll = EnrollCourse.objects.create(user=self.user, course=self.old_course, semester=self.semester)

    def test_merge_course(self):
        user2 = User.objects.create(username="test2")
        new_course = Course.objects.create(code='NEW1500', main_teacher=self.old_teacher)
        enroll2 = EnrollCourse.objects.create(user=user2, course=new_course, semester=self.semester)
        enroll3 = EnrollCourse.objects.create(user=user2, course=self.old_course, semester=self.semester)
        merge_course(self.old_course, new_course)
        new_course = Course.objects.get(code='NEW1500', main_teacher=self.old_teacher)
        self.assertFalse(Course.objects.filter(code='CS1500').exists())
        self.assertEqual(Review.objects.get(pk=self.old_review.pk).course_id, new_course.pk)
        self.assertEqual(new_course.review_count, 1)
        self.assertEqual(new_course.review_avg, 3)
        # 旧的被修改为新的
        self.assertEqual(EnrollCourse.objects.get(pk=self.enroll.pk).course_id, new_course.pk)
        # 重复的被删掉
        self.assertFalse(EnrollCourse.objects.filter(pk=enroll3.pk).exists())
        # 新的不变
        self.assertEqual(EnrollCourse.objects.get(pk=enroll2.pk).course, new_course)

    def test_merge_course_by_id(self):
        self.assertEqual(merge_course_by_id(10, 20), False)
        new_course = Course.objects.create(code='NEW1500', main_teacher=self.old_teacher)
        self.assertEqual(merge_course_by_id(self.old_course.pk, new_course.pk), True)

    def test_merge_teacher_move(self):
        new_teacher = Teacher.objects.create(name='高女士2')
        merge_teacher(self.old_teacher, new_teacher)
        self.assertEqual(Course.objects.get(code='CS1500').main_teacher, new_teacher)

    def test_merge_teacher_merge(self):
        old_teacher = Teacher.objects.get(tid=2, name='梁女士')
        new_teacher = Teacher.objects.get(tid=3, name='赵先生')
        create_review('test', 'MARX1001', 3)
        merge_teacher(old_teacher, new_teacher)
        self.assertEqual(Course.objects.filter(code='MARX1001').count(), 1)
        course = Course.objects.get(code='MARX1001')
        self.assertEqual(course.review_count, 1)
        self.assertEqual(course.review_avg, 3)

    def test_merge_teacher_by_id(self):
        self.assertEqual(merge_teacher_by_id(10, 20), False)
        old_teacher = Teacher.objects.get(tid=2, name='梁女士')
        new_teacher = Teacher.objects.get(tid=3, name='赵先生')
        self.assertEqual(merge_teacher_by_id(old_teacher.pk, new_teacher.pk), True)

    def test_replace_code_move(self):
        replace_course_code_multi('CS1500', 'NEW1500')
        self.assertEqual(Course.objects.get(pk=self.old_course.pk).code, 'NEW1500')

    def test_replace_code_merge(self):
        Course.objects.create(code='NEW1500', main_teacher=self.old_teacher)
        replace_course_code_multi('CS1500', 'NEW1500')
        self.assertFalse(Course.objects.filter(pk=self.old_course.pk).exists())
        new_course = Course.objects.get(code='NEW1500', main_teacher=self.old_teacher)
        self.assertEqual(Review.objects.get(pk=self.old_review.pk).course_id, new_course.pk)
        self.assertEqual(new_course.review_count, 1)
        self.assertEqual(new_course.review_avg, 3)


class ExportTest(TestCase):

    def setUp(self) -> None:
        create_test_env()

    def test_export(self):
        sio = StringIO()
        export_courses_to_csv(sio)
        self.assertEqual(sio.getvalue(),
                         "code,name,main_teacher,id\r\n"
                         f"CS1500,计算机科学导论,高女士,{Course.objects.get(code='CS1500').pk}\r\n"
                         f"CS2500,算法与复杂性,高女士,{Course.objects.get(code='CS2500').pk}\r\n"
                         f"MARX1001,思想道德修养与法律基础,梁女士,{Course.objects.get(code='MARX1001', main_teacher__name='梁女士').pk}\r\n"
                         f"MARX1001,思想道德修养与法律基础,赵先生,{Course.objects.get(code='MARX1001', main_teacher__name='赵先生').pk}\r\n")
        sio.close()
