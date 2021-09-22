# Generated by Django 3.2.7 on 2021-09-22 14:12

from django.db import migrations, models
from django.db.models import Count, Avg


def compute_course_review(apps, schema_editor):
    Course = apps.get_model('jcourse_api', 'Course')
    Review = apps.get_model('jcourse_api', 'Review')
    courses = Course.objects.annotate(count=Count('review')).filter(count__gt=0)
    for course in courses:
        reviews = Review.objects.filter(course=course)
        course.review_count = reviews.count()
        course.review_avg = reviews.aggregate(avg=Avg('rating'))['avg']
        course.save()


def compute_review_action(apps, schema_editor):
    Review = apps.get_model('jcourse_api', 'Review')
    Action = apps.get_model('jcourse_api', 'Action')
    reviews = Review.objects.annotate(count=Count('action')).filter(count__gt=0)
    for review in reviews:
        actions = Action.objects.filter(review=review)
        review.approve_count = actions.filter(action=1).count()
        review.disapprove_count = actions.filter(action=-1).count()
        review.save()


class Migration(migrations.Migration):
    dependencies = [
        ('jcourse_api', '0006_alter_teacher_title'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='review',
            name='available',
        ),
        migrations.AddField(
            model_name='course',
            name='review_avg',
            field=models.FloatField(blank=True, default=0, null=True, verbose_name='平均评分'),
        ),
        migrations.AddField(
            model_name='course',
            name='review_count',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='点评数'),
        ),
        migrations.AddField(
            model_name='review',
            name='approve_count',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='获赞数'),
        ),
        migrations.AddField(
            model_name='review',
            name='disapprove_count',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='获踩数'),
        ),
        migrations.RunPython(compute_course_review),
        migrations.RunPython(compute_review_action)
    ]
