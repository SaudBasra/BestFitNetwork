from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divides the value by the argument
    """
    try:
        return Decimal(value) / Decimal(arg) if Decimal(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """
    Multiplies the value by the argument
    """
    try:
        return Decimal(value) * Decimal(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """
    Subtracts arg from value
    """
    try:
        return Decimal(value) - Decimal(arg)
    except (ValueError, TypeError):
        return 0
