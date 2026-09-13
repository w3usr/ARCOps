"""`{{ mapping|dictkey:key }}`: a lookup with a variable key, which Django's dot syntax cannot do."""

from django import template

register = template.Library()


@register.filter
def dictkey(mapping, key):
    try:
        return mapping.get(key, "")
    except AttributeError:
        return ""
