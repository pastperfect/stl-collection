"""
Quick verification script for STL Collection Manager
This script checks if all components are properly configured
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from django.contrib.auth.models import User
from tags.models import Tag
from image_upload.models import Image
from django.urls import reverse
from django.test import Client

def test_basic_functionality():
    print("=== STL Collection Manager - System Check ===\n")
    
    # Check database models
    print("1. Database Models:")
    print(f"   ✓ Tags: {Tag.objects.count()} available")
    print(f"   ✓ Images: {Image.objects.count()} uploaded")
    print(f"   ✓ Users: {User.objects.count()} registered")
    
    # Check admin user
    admin_exists = User.objects.filter(username='admin').exists()
    print(f"   ✓ Admin user: {'Available' if admin_exists else 'Not created'}")
    
    print("\n2. URL Configuration:")
    
    # Test basic URL patterns
    client = Client()
    
    urls_to_test = [
        ('/', 'Landing page'),
        ('/collection/', 'Collection gallery'),
        ('/admin/', 'Admin interface'),
    ]
    
    for url, description in urls_to_test:
        try:
            response = client.get(url)
            status = "✓" if response.status_code in [200, 302] else "✗"
            print(f"   {status} {description}: {response.status_code}")
        except Exception as e:
            print(f"   ✗ {description}: Error - {str(e)}")
    
    print("\n3. Template Files:")
    template_files = [
        'templates/base.html',
        'templates/landing_page.html',
        'templates/collection/gallery.html',
        'templates/image_upload/upload.html'
    ]
    
    for template in template_files:
        exists = os.path.exists(template)
        status = "✓" if exists else "✗"
        print(f"   {status} {template}")
    
    print("\n4. Media Configuration:")
    media_dir = os.path.exists('media/uploaded_images')
    status = "✓" if media_dir else "✗"
    print(f"   {status} Media directory: media/uploaded_images/")
    
    print("\n=== System Check Complete ===")
    print("\nTo test the application:")
    print("1. Run: python manage.py runserver")
    print("2. Visit: http://127.0.0.1:8000")
    print("3. Admin: http://127.0.0.1:8000/admin (admin/admin123)")
    print("4. Upload some test STL files and assign tags")

if __name__ == "__main__":
    test_basic_functionality()
