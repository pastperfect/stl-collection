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


@register.filter
def get_param(query_dict, param_name):
    """
    Get a parameter from a QueryDict
    Usage: {{ request.GET|get_param:'tag_type_1' }}
    """
    if hasattr(query_dict, 'get'):
        return query_dict.get(param_name, '')
    return ''
