"""Django Portal UI configuration."""

from django.conf import settings


def get_config():
    """Get portal UI configuration from settings."""
    defaults = {
        # Site branding
        'SITE_NAME': 'Portal',
        'SITE_LOGO': None,
        'PRIMARY_COLOR': 'primary',  # Tailwind color name

        # Footer
        'SHOW_FOOTER': True,
        'FOOTER_TEXT': '',

        # Navigation for each portal context
        'PUBLIC_NAV': [],
        'PORTAL_NAV': [],
        'STAFF_NAV': [],
        'SUPERADMIN_NAV': [],

        # Legacy support
        'SIDEBAR_ITEMS': [],
        'USER_MENU_ITEMS': [],

        # URL prefixes for portal contexts
        'PORTAL_PREFIX': '/portal/',
        'STAFF_PREFIX': '/staff/',
        'SUPERADMIN_PREFIX': '/superadmin/',

        # Login URL
        'LOGIN_URL': '/accounts/login/',
    }

    user_config = getattr(settings, 'PORTAL_UI', {})
    return {**defaults, **user_config}


def get_setting(name, default=None):
    """Get a specific portal UI setting."""
    config = get_config()
    return config.get(name, default)


def get_sidebar_items():
    """Get configured sidebar navigation items (legacy)."""
    config = get_config()
    return config.get('SIDEBAR_ITEMS', [])


def get_public_nav():
    """Get public website navigation items."""
    config = get_config()
    return config.get('PUBLIC_NAV', [])


def get_portal_nav():
    """Get customer portal navigation items."""
    config = get_config()
    return config.get('PORTAL_NAV', [])


def get_staff_nav():
    """Get staff portal navigation items."""
    config = get_config()
    return config.get('STAFF_NAV', [])


def get_superadmin_nav():
    """Get superadmin navigation items."""
    config = get_config()
    return config.get('SUPERADMIN_NAV', [])


def get_site_name():
    """Get the configured site name."""
    config = get_config()
    return config.get('SITE_NAME', 'Portal')


def get_login_url():
    """Get the login URL."""
    config = get_config()
    return config.get('LOGIN_URL', '/accounts/login/')
