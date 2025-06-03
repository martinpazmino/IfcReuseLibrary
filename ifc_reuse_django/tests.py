from django.test import TestCase
from django.urls import reverse

class SimpleTest(TestCase):
    def test_homepage_loads(self):
        response = self.client.get(reverse('home'))  # Falls du eine URL namens 'home' hast
        self.assertEqual(response.status_code, 200)
