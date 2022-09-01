from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from oauth.views import get_or_create_user, hash_username


class SendCodeTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.endpoint = '/oauth/email/send-code/'

    @patch('rest_framework.throttling.UserRateThrottle.allow_request')
    @patch('jcourse.throttles.EmailCodeRateThrottle.allow_request')
    def test_view(self, email_throttle, user_throttle):
        email_throttle.return_value = True
        user_throttle.return_value = True
        resp = self.client.get(self.endpoint)
        self.assertEqual(resp.status_code, 405)
        resp = self.client.post(self.endpoint, data={"email": "xxx@fdu.edu.cn"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.endpoint, data={"email": "xxx"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.endpoint)
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.endpoint, data={"email": "xxx@sjtu.edu.cn"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '选课社区验证码')

    def test_throttle(self):
        resp = self.client.post(self.endpoint, data={"email": "xxx@sjtu.edu.cn"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(self.endpoint, data={"email": "xxx@sjtu.edu.cn"})
        self.assertEqual(resp.status_code, 429)


class VerifyCodeTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.endpoint = '/oauth/email/verify/'

    @patch('rest_framework.throttling.UserRateThrottle.allow_request')
    @patch('jcourse.throttles.VerifyEmailRateThrottle.allow_request')
    def test_wrong_input(self, email_throttle, user_throttle):
        email_throttle.return_value = True
        user_throttle.return_value = True
        resp = self.client.post(self.endpoint, data={"code": "xxx"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.endpoint, data={"email": "xxx@sjtu.edu.cn"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.endpoint)
        self.assertEqual(resp.status_code, 400)
        resp = self.client.get(self.endpoint)
        self.assertEqual(resp.status_code, 405)

    def test_not_sent_code(self):
        resp = self.client.post(self.endpoint, data={"email": "xxx@sjtu.edu.cn", "code": "123456"})
        self.assertEqual(resp.status_code, 400)

    @patch('rest_framework.throttling.UserRateThrottle.allow_request')
    @patch('jcourse.throttles.VerifyEmailRateThrottle.allow_request')
    def test_valid(self, email_throttle, user_throttle):
        email_throttle.return_value = True
        user_throttle.return_value = True
        email = "xxx@sjtu.edu.cn"
        resp = self.client.post('/oauth/email/send-code/', data={"email": email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '选课社区验证码')
        code = cache.get(email)
        self.assertIsNotNone(code)
        resp = self.client.post(self.endpoint, data={"email": email, "code": code})
        self.assertEqual(resp.status_code, 200)


class GetOrCreateUserTest(TestCase):
    def test_lower_first_upper_last(self):
        username = hash_username("abc")

        get_or_create_user("abc")
        user = User.objects.get()
        self.assertEqual(user.username, username)

        get_or_create_user("Abc")
        user = User.objects.get()
        self.assertEqual(user.username, username)

    def test_exactly_the_same(self):
        username = hash_username("abc")

        get_or_create_user("abc")
        user = User.objects.get()
        self.assertEqual(user.username, username)

        get_or_create_user("abc")
        user = User.objects.get()
        self.assertEqual(user.username, username)

    def test_upper_first_low_last(self):
        User.objects.create(username=hash_username("Abc"))
        get_or_create_user("abc")
        get_or_create_user("Abc")
        self.assertEqual(User.objects.count(), 2)
