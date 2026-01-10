"""
API endpoints for bulk import operations via HTTP.
These endpoints use HTTP Basic Authentication and can be called from standalone scripts.
"""

import json
import os
import re
import uuid
import base64
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.db import transaction
from .models import Entry, Image
from tags.models import Tag, TagType


def to_camel_case(text):
    """Convert text to camelCase format"""
    if not text:
        return "unknown"
    words = re.split(r'[^a-zA-Z0-9]+', str(text).strip())
    words = [word for word in words if word]
    if not words:
        return "unknown"
    camel_case = words[0].lower()
    for word in words[1:]:
        camel_case += word.capitalize()
    return camel_case


def require_basic_auth(view_func):
    """Decorator to require HTTP Basic Authentication"""
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Basic '):
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401, headers={'WWW-Authenticate': 'Basic realm="API"'})
        
        try:
            auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = auth_decoded.split(':', 1)
            user = authenticate(username=username, password=password)
            
            if user is None or not user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid credentials or insufficient permissions'
                }, status=401)
            
            request.user = user
            return view_func(request, *args, **kwargs)
        except Exception:
            return JsonResponse({
                'success': False,
                'error': 'Authentication failed'
            }, status=401)
    
    return wrapper


@csrf_exempt
@require_http_methods(["GET"])
@require_basic_auth
def api_health(request):
    """
    Health check endpoint.
    GET /upload/api/health/
    Returns: {"success": true, "status": "ok", "authenticated": true, "username": "..."}
    """
    return JsonResponse({
        'success': True,
        'status': 'ok',
        'authenticated': True,
        'username': request.user.username
    })


@csrf_exempt
@require_http_methods(["GET"])
@require_basic_auth
def api_check_duplicate(request):
    """
    Check if an entry already exists.
    GET /upload/api/check-duplicate/?name=X&publisher=Y&range=Z
    Returns: {"success": true, "exists": true/false, "entry_id": id, "entry_name": "..."}
    """
    name = request.GET.get('name', '').strip()
    publisher = request.GET.get('publisher', '').strip()
    range_name = request.GET.get('range', '').strip()
    
    if not name:
        return JsonResponse({
            'success': False,
            'error': 'Name parameter required'
        }, status=400)
    
    # Check for duplicate
    entry = Entry.objects.filter(
        name__iexact=name,
        publisher__iexact=publisher if publisher else '',
        range__iexact=range_name if range_name else ''
    ).first()
    
    if entry:
        return JsonResponse({
            'success': True,
            'exists': True,
            'entry_id': entry.id,
            'entry_name': entry.name
        })
    else:
        return JsonResponse({
            'success': True,
            'exists': False
        })


@csrf_exempt
@require_http_methods(["GET"])
@require_basic_auth
def api_get_tags(request):
    """
    Get all existing tags grouped by tag type.
    GET /upload/api/get-tags/
    Returns: {"success": true, "tags": {"Publisher": ["Tag1", "Tag2"], "Faction Tag": [...]}}
    """
    try:
        # Get all tag types
        tag_types = TagType.objects.all()
        
        tags_by_type = {}
        for tag_type in tag_types:
            # Get all tags for this type
            tags = Tag.objects.filter(tag_type=tag_type).values_list('name', flat=True)
            tags_by_type[tag_type.name] = list(tags)
        
        return JsonResponse({
            'success': True,
            'tags': tags_by_type
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_POST
@require_basic_auth
def api_create_entry(request):
    """
    Create a new entry with tags.
    POST /upload/api/create-entry/
    Body: {
        "name": "Entry Name",
        "publisher": "Publisher Name",
        "range": "Range Name",
        "folder_location": "Original folder path",
        "tags": {
            "Publisher": ["Tag1"],
            "Faction Tag": ["Tag2"],
            "Army Role": ["Tag3"],
            "GW Alternative": ["Tag4", "Tag5"]
        }
    }
    Returns: {"success": true, "entry_id": 123, "entry_name": "...", "tags_assigned": 5}
    """
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        publisher = data.get('publisher', '').strip()
        range_name = data.get('range', '').strip()
        folder_location = data.get('folder_location', '').strip()
        tags_data = data.get('tags', {})
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Name is required'
            }, status=400)
        
        # Check for duplicate
        existing = Entry.objects.filter(
            name__iexact=name,
            publisher__iexact=publisher if publisher else '',
            range__iexact=range_name if range_name else ''
        ).first()
        
        if existing:
            return JsonResponse({
                'success': False,
                'error': 'Entry already exists',
                'entry_id': existing.id
            }, status=409)
        
        with transaction.atomic():
            # Create entry
            entry = Entry.objects.create(
                name=name,
                publisher=publisher or None,
                range=range_name or None,
                folder_location=folder_location or None
            )
            
            # Tag type configurations
            tag_type_configs = {
                'Publisher': {'color': '#3498db', 'sort_order': 10},
                'Faction Tag': {'color': '#e74c3c', 'sort_order': 20},
                'Army Role': {'color': '#2ecc71', 'sort_order': 30},
                'GW Alternative': {'color': '#f39c12', 'sort_order': 40}
            }
            
            all_tags = []
            
            # Create or get tags
            for tag_type_name, config in tag_type_configs.items():
                # Get or create tag type
                tag_type, _ = TagType.objects.get_or_create(
                    name=tag_type_name,
                    defaults={
                        'description': f'{tag_type_name} tags',
                        'color': config['color'],
                        'sort_order': config['sort_order'],
                        'is_active': True,
                        'show_in_gallery': True,
                        'set_at_upload': True
                    }
                )
                
                # Get tag names for this type
                tag_names = tags_data.get(tag_type_name, [])
                for tag_name in tag_names:
                    tag_name = tag_name.strip()
                    if tag_name:
                        tag, _ = Tag.objects.get_or_create(
                            name=tag_name,
                            defaults={'tag_type': tag_type}
                        )
                        all_tags.append(tag)
            
            # Assign tags to entry
            if all_tags:
                entry.tags.add(*all_tags)
            
            return JsonResponse({
                'success': True,
                'entry_id': entry.id,
                'entry_name': entry.name,
                'tags_assigned': len(all_tags)
            }, status=201)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_POST
@require_basic_auth
def api_upload_image(request):
    """
    Upload an image for an entry.
    POST /upload/api/upload-image/
    Body: multipart/form-data
        - entry_id: Entry ID
        - image: Image file
        - is_primary: "true" or "false"
    Returns: {"success": true, "image_id": 123, "filename": "...", "is_primary": true/false}
    """
    try:
        entry_id = request.POST.get('entry_id')
        is_primary = request.POST.get('is_primary', 'false').lower() == 'true'
        
        if not entry_id:
            return JsonResponse({
                'success': False,
                'error': 'entry_id is required'
            }, status=400)
        
        if 'image' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'image file is required'
            }, status=400)
        
        entry = Entry.objects.filter(id=entry_id).first()
        if not entry:
            return JsonResponse({
                'success': False,
                'error': f'Entry {entry_id} not found'
            }, status=404)
        
        uploaded_file = request.FILES['image']
        
        # Get file extension
        _, ext = os.path.splitext(uploaded_file.name)
        
        # Generate filename using camelCase format
        publisher = to_camel_case(entry.publisher)
        range_name = to_camel_case(entry.range)
        name = to_camel_case(entry.name)
        unique_id = uuid.uuid4().hex[:8]
        
        new_filename = f"{publisher}_{range_name}_{name}_{unique_id}{ext}"
        
        # Create Image instance
        image = Image(
            entry=entry,
            name=entry.name,
            publisher=entry.publisher,
            range=entry.range,
            is_primary=is_primary
        )
        
        # Read file content and save with new name
        file_content = uploaded_file.read()
        image.image.save(new_filename, ContentFile(file_content), save=False)
        image.save()
        
        return JsonResponse({
            'success': True,
            'image_id': image.id,
            'filename': new_filename,
            'is_primary': image.is_primary
        }, status=201)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
