"""Context processors for django-portal-ui."""

from django.urls import reverse, NoReverseMatch

from . import conf


def get_portal_context(request):
    """
    Determine portal context based on URL path.

    Returns: 'public', 'portal', 'staff', or 'superadmin'
    """
    path = request.path

    config = conf.get_config()
    portal_prefix = config.get('PORTAL_PREFIX', '/portal/')
    staff_prefix = config.get('STAFF_PREFIX', '/staff/')
    superadmin_prefix = config.get('SUPERADMIN_PREFIX', '/superadmin/')

    if path.startswith(superadmin_prefix):
        return 'superadmin'
    elif path.startswith(staff_prefix):
        return 'staff'
    elif path.startswith(portal_prefix):
        return 'portal'
    else:
        return 'public'


def resolve_nav_url(item, request):
    """
    Resolve navigation item URL.

    Supports both named URLs and path strings.
    """
    url = item.get('url', '')

    if not url:
        return '#'

    # If it starts with / or http, it's a direct URL
    if url.startswith('/') or url.startswith('http'):
        return url

    # Try to resolve as named URL
    try:
        return reverse(url)
    except NoReverseMatch:
        # Maybe it's a path, return as-is
        return url


def filter_nav_items(items, user, request):
    """
    Filter navigation items based on user permissions.

    Each item can have:
    - 'permission': 'module.action' - requires this permission
    - 'staff_only': True - requires is_staff
    - 'superuser_only': True - requires is_superuser
    """
    filtered = []

    for item in items:
        # Check superuser requirement
        if item.get('superuser_only') and not user.is_superuser:
            continue

        # Check staff requirement
        if item.get('staff_only') and not user.is_staff:
            continue

        # Check module permission
        permission = item.get('permission')
        if permission:
            if user.is_superuser:
                pass  # Superusers have all permissions
            elif hasattr(user, 'has_module_permission'):
                # Using django-accounts
                parts = permission.split('.')
                module = parts[0]
                action = parts[1] if len(parts) > 1 else 'view'
                if not user.has_module_permission(module, action):
                    continue
            elif not user.has_perm(permission):
                continue

        # Resolve URL and add to filtered list
        nav_item = item.copy()
        nav_item['resolved_url'] = resolve_nav_url(item, request)
        nav_item['is_active'] = request.path.startswith(nav_item['resolved_url'])
        filtered.append(nav_item)

    return filtered


def get_navigation_for_context(context, user, request):
    """Get navigation items for the given portal context."""
    if context == 'superadmin':
        items = conf.get_superadmin_nav()
    elif context == 'staff':
        items = conf.get_staff_nav()
    elif context == 'portal':
        items = conf.get_portal_nav()
    else:
        items = conf.get_public_nav()

    # Filter based on user permissions
    if user.is_authenticated:
        return filter_nav_items(items, user, request)
    else:
        # Anonymous users only see items without permission requirements
        return [
            {**item, 'resolved_url': resolve_nav_url(item, request)}
            for item in items
            if not item.get('permission') and not item.get('staff_only') and not item.get('superuser_only')
        ]


def group_nav_by_section(items):
    """Group navigation items by section."""
    sections = {}
    for item in items:
        section = item.get('section', 'Main')
        if section not in sections:
            sections[section] = []
        sections[section].append(item)
    return sections


def portal_ui(request):
    """Add portal UI configuration to template context."""
    config = conf.get_config()
    portal_context = get_portal_context(request)
    user = request.user if hasattr(request, 'user') else None

    # Get navigation for current context
    if user:
        navigation = get_navigation_for_context(portal_context, user, request)
    else:
        navigation = []

    # Group by section for sidebar rendering
    nav_sections = group_nav_by_section(navigation)

    return {
        'portal_ui': {
            # Site branding
            'site_name': config.get('SITE_NAME'),
            'site_logo': config.get('SITE_LOGO'),
            'primary_color': config.get('PRIMARY_COLOR'),

            # Portal context
            'context': portal_context,
            'is_public': portal_context == 'public',
            'is_portal': portal_context == 'portal',
            'is_staff': portal_context == 'staff',
            'is_superadmin': portal_context == 'superadmin',

            # Navigation
            'navigation': navigation,
            'nav_sections': nav_sections,

            # Legacy support
            'sidebar_items': conf.get_sidebar_items(),
            'user_menu_items': config.get('USER_MENU_ITEMS', []),

            # Footer
            'show_footer': config.get('SHOW_FOOTER', True),
            'footer_text': config.get('FOOTER_TEXT', ''),

            # URLs
            'login_url': config.get('LOGIN_URL', '/accounts/login/'),
            'portal_prefix': config.get('PORTAL_PREFIX', '/portal/'),
            'staff_prefix': config.get('STAFF_PREFIX', '/staff/'),
            'superadmin_prefix': config.get('SUPERADMIN_PREFIX', '/superadmin/'),
        }
    }
