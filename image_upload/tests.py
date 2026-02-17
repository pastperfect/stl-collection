import tempfile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Entry, STLFile


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class STLFileTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='tester',
			email='tester@example.com',
			password='password123'
		)
		self.entry = Entry.objects.create(
			name='Test Model',
			publisher='Test Publisher',
			range='Test Range'
		)

	def test_stl_upload_path_structure(self):
		upload = SimpleUploadedFile('Sample File.zip', b'zipcontent')
		stl_file = STLFile.objects.create(
			entry=self.entry,
			file=upload,
			original_name=upload.name,
			uploaded_by=self.user
		)

		self.assertIn('stlFiles/', stl_file.file.name)
		self.assertIn('test-publisher/test-range/test-model/', stl_file.file.name)

	def test_add_stl_files_rejects_invalid_extension(self):
		self.client.login(username='tester', password='password123')
		upload = SimpleUploadedFile('not_allowed.txt', b'nope')
		url = reverse('image_upload:add_stl_files', args=[self.entry.id])

		response = self.client.post(url, {'stl_files': upload})
		self.assertEqual(response.status_code, 400)
