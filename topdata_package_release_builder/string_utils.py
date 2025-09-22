"""A collection of utility functions for string manipulation and case conversion."""

import re


def camel_to_kebab_for_composer(camel_str: str) -> str:
    """
    Convert a CamelCase string to kebab-case for composer.json package names.
    Example: 'FreeTopdataPlugin' -> 'free-topdata-plugin'
    """
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1-\2', camel_str)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def camel_to_kebab_for_js_asset(name: str) -> str:
    """
    Convert CamelCase to kebab-case, correctly handling acronyms and numbers for JS assets.
    Example: 'TopdataCategorySW6' -> 'topdata-category-s-w-6'
    """
    # Insert hyphen before uppercase letter followed by lowercase (e.g., Plugin -> -Plugin)
    name = re.sub(r'([A-Z])([a-z])', r'-\1\2', name)
    # Insert hyphen before uppercase letter preceded by a non-uppercase char (e.g., myPlugin -> my-Plugin)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', name)
    # Insert hyphen between letters and numbers (e.g., SW6 -> SW-6)
    name = re.sub(r'([A-Z])([0-9])', r'\1-\2', name)
    # Insert hyphen between consecutive uppercase letters (e.g., SW -> S-W)
    name = re.sub(r'([A-Z])([A-Z])', r'\1-\2', name)
    return name.lstrip('-').lower()


def prepend_variant_text(text: str, prefix: str, suffix: str) -> str:
    """
    Prepend prefix/suffix to text in a consistent format like '[PREFIX] [SUFFIX] Text'.
    It also removes any existing variant markers to prevent duplication.
    """
    variant_text = ""

    if prefix:
        variant_text += f"[{prefix.upper()}] "

    if suffix:
        variant_text += f"[{suffix.upper()}] "

    # Remove existing variant markers if they exist to avoid duplication
    text = re.sub(r'^(\[[A-Z]+\]\s*)+', '', text)

    return variant_text + text
