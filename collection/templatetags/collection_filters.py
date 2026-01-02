"""
Custom template filters for the collection app
"""
from django import template

register = template.Library()


@register.filter
def dict_item(dictionary, key):
    """
    Get an item from a dictionary by key
    Usage: {{ my_dict|dict_item:key_variable }}
    """
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
