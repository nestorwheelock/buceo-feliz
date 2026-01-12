# django-portal-ui

A complete portal/dashboard UI framework for Django applications. Provides separate layouts for public websites, customer portals, staff dashboards, and admin panels - all with role-based navigation and Tailwind CSS styling.

## Features

- **Multi-Portal Architecture**: Separate UI contexts for public, customer, staff, and superadmin
- **Role-Based Navigation**: Menus automatically adapt based on user role (not just URL)
- **Responsive Layouts**: Mobile-friendly sidebars with Alpine.js interactions
- **Base Templates**: Ready-to-use templates that other django-* packages can extend
- **Icon Components**: Feather icons as inline SVGs
- **UI Components**: Cards, tables, stats, messages
- **Permission Filtering**: Navigation items filtered by user permissions
- **Configurable**: All settings via Django's `PORTAL_UI` dict

## Installation

```bash
pip install django-portal-ui
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'django_portal_ui',
]
```

Add the context processor:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_portal_ui.context_processors.portal_ui',  # Add this
            ],
        },
    },
]
```

## Portal Architecture

django-portal-ui provides four portal contexts, each with its own layout and navigation:

| Context | URL Prefix | Target Users | Base Template |
|---------|-----------|--------------|---------------|
| Public | `/` | Anonymous visitors | `base_public.html` |
| Portal | `/portal/` | Authenticated customers | `base_portal.html` |
| Staff | `/staff/` | Staff members | `base_staff.html` |
| Superadmin | `/superadmin/` | Superusers only | `base_superadmin.html` |

### Smart Context Detection

The portal context is determined by **user role first**, then URL path:

- **Superusers** → See superadmin navigation everywhere
- **Staff users** → See staff navigation everywhere
- **Authenticated users** → See portal navigation
- **Anonymous users** → See public navigation

URL paths can override (e.g., a superuser visiting `/portal/` sees portal nav).

## Configuration

Configure via the `PORTAL_UI` setting in `settings.py`:

```python
PORTAL_UI = {
    # Branding
    'SITE_NAME': 'My Application',
    'SITE_LOGO': '/static/images/logo.png',  # Optional
    'PRIMARY_COLOR': 'primary',  # Tailwind color name

    # Footer
    'SHOW_FOOTER': True,
    'FOOTER_TEXT': 'Copyright 2025 My Company',

    # URL Prefixes (customize if needed)
    'PORTAL_PREFIX': '/portal/',
    'STAFF_PREFIX': '/staff/',
    'SUPERADMIN_PREFIX': '/superadmin/',
    'LOGIN_URL': '/accounts/login/',

    # Navigation for each context
    'PUBLIC_NAV': [
        {'label': 'Home', 'url': '/', 'icon': 'home'},
        {'label': 'About', 'url': '/about/', 'icon': 'info'},
        {'label': 'Contact', 'url': '/contact/', 'icon': 'mail'},
    ],

    'PORTAL_NAV': [
        {'label': 'Dashboard', 'url': 'portal:dashboard', 'icon': 'home', 'section': 'Main'},
        {'label': 'My Profile', 'url': 'portal:profile', 'icon': 'user', 'section': 'Account'},
        {'label': 'My Orders', 'url': 'portal:orders', 'icon': 'shopping-bag', 'section': 'Account'},
    ],

    'STAFF_NAV': [
        {'label': 'Dashboard', 'url': 'staff:dashboard', 'icon': 'home', 'section': 'Hub'},
        {'label': 'Customers', 'url': 'staff:customers', 'icon': 'users', 'section': 'CRM'},
        {'label': 'Orders', 'url': 'staff:orders', 'icon': 'package', 'section': 'Operations'},
        {'label': 'Reports', 'url': 'staff:reports', 'icon': 'bar-chart-2', 'section': 'Analytics'},
    ],

    'SUPERADMIN_NAV': [
        {'label': 'Dashboard', 'url': 'superadmin:dashboard', 'icon': 'home', 'section': 'Admin'},
        {'label': 'Users', 'url': 'superadmin:users', 'icon': 'users', 'section': 'Admin'},
        {'label': 'Roles', 'url': 'superadmin:roles', 'icon': 'shield', 'section': 'Admin'},
        {'label': 'Audit Log', 'url': 'superadmin:audit', 'icon': 'activity', 'section': 'Admin'},
    ],
}
```

### Navigation Item Options

Each navigation item supports:

```python
{
    'label': 'Dashboard',           # Display text (required)
    'url': 'app:view_name',         # URL name or path (required)
    'icon': 'home',                 # Feather icon name
    'section': 'Main',              # Sidebar section grouping
    'permission': 'module.action',  # Required permission (optional)
    'staff_only': True,             # Only show to staff (optional)
    'superuser_only': True,         # Only show to superusers (optional)
}
```

## Templates

### Template Hierarchy

```
templates/
├── base.html                    → Root base (includes Tailwind, Alpine.js)
├── base_public.html             → Public website layout
├── base_portal.html             → Customer portal with sidebar
├── base_staff.html              → Staff dashboard with sidebar
├── base_superadmin.html         → Admin panel with sidebar
└── components/
    └── icons/
        └── feather.html         → SVG icon component
```

### Using Base Templates

Other django-* packages extend these templates:

```html
{% extends "base_staff.html" %}
{% load portal_ui_tags %}

{% block breadcrumb %}
<li>
    <div class="flex items-center">
        <svg class="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
        </svg>
        <span class="ml-2 text-sm font-medium text-gray-700">My Page</span>
    </div>
</li>
{% endblock %}

{% block staff_content %}
<div class="bg-white shadow-sm rounded-lg p-6">
    <h1 class="text-2xl font-bold">My Staff Page</h1>
    <!-- Your content here -->
</div>
{% endblock %}
```

### Available Blocks

| Block | Description |
|-------|-------------|
| `title` | Page title in `<title>` tag |
| `extra_css` | Additional CSS in `<head>` |
| `extra_js` | Additional JS before `</body>` |
| `breadcrumb` | Breadcrumb navigation items |
| `header_actions` | Buttons/actions in header bar |
| `content` | Main page content |
| `staff_content` | Staff page content (alias for content) |

## Icons

### Using the Icon Template Tag

```html
{% load portal_ui_tags %}

{% icon "home" %}
{% icon "users" "w-6 h-6" %}
{% icon "check" "w-4 h-4 text-green-500" %}
```

### Using the Icon Include

```html
{% include "components/icons/feather.html" with icon="home" class="w-5 h-5" %}
```

### Available Icons

**General:** `activity`, `alert-circle`, `bar-chart`, `bell`, `briefcase`, `calendar`, `check`, `chevron-down`, `chevron-right`, `clipboard`, `credit-card`, `database`, `dollar-sign`, `edit`, `file-text`, `gift`, `grid`, `heart`, `home`, `image`, `inbox`, `info`, `layers`, `log-out`, `menu`, `package`, `paw`, `pill`, `plus`, `search`, `settings`, `shield`, `shopping-bag`, `star`, `trash`, `truck`, `user`, `users`, `x`

**Marine/Diving:** `anchor`, `compass`, `life-buoy`, `waves`

## Components

### Card Component

```html
{% include "portal_ui/components/card.html" with title="Statistics" %}
```

### Messages Component

Automatically renders Django messages with appropriate styling:

```html
{% include "portal_ui/components/messages.html" %}
```

### Stats Component

```html
{% include "portal_ui/components/stats.html" with stats=stats_list %}
```

Where `stats_list` is:
```python
stats_list = [
    {'label': 'Total Users', 'value': '1,234', 'icon': 'users', 'change': '+12%'},
    {'label': 'Revenue', 'value': '$45,678', 'icon': 'dollar-sign', 'change': '+8%'},
]
```

### Table Component

```html
{% include "portal_ui/components/table.html" with headers=headers rows=rows %}
```

## Form Components

Tailwind-styled form components for building consistent forms.

### Field Component

Renders a complete form field with label, input, help text, and errors:

```html
{% load portal_ui_tags %}
{% include "portal_ui/components/forms/field.html" with field=form.name %}
{% include "portal_ui/components/forms/field.html" with field=form.email %}
```

Features:
- Label with required indicator (*)
- Tailwind-styled input with focus states
- Help text display (gray, small)
- Error message display (red)

### Button Component

Renders styled buttons with variant support:

```html
{# Primary button (default) #}
{% include "portal_ui/components/forms/button.html" with type="submit" text="Save" variant="primary" %}

{# Secondary button #}
{% include "portal_ui/components/forms/button.html" with type="button" text="Cancel" variant="secondary" %}

{# Danger button #}
{% include "portal_ui/components/forms/button.html" with type="button" text="Delete" variant="danger" %}
```

### Form Errors Component

Renders non-field form errors:

```html
{% include "portal_ui/components/forms/form_errors.html" with form=form %}
```

### Eligibility Alert Component

Displays eligibility check results (for decisioning systems):

```html
{% include "portal_ui/components/forms/eligibility_alert.html" with result=eligibility %}
```

Expects `result` with:
- `allowed`: Boolean indicating if action is allowed
- `reasons`: List of reasons why not allowed
- `required_actions`: List of actions needed to become eligible

### add_class Filter

Add CSS classes to form field widgets:

```html
{% load portal_ui_tags %}

{{ form.name|add_class:"w-full px-3 py-2 border rounded-lg" }}
{{ form.email|add_class:"w-full px-3 py-2 border rounded-lg focus:ring-2" }}
```

If the widget already has classes, new classes are appended.

## Context Variables

The `portal_ui` context processor provides these variables in all templates:

```python
{{ portal_ui.site_name }}        # Configured site name
{{ portal_ui.site_logo }}        # Logo URL (if configured)
{{ portal_ui.context }}          # Current context: 'public', 'portal', 'staff', 'superadmin'
{{ portal_ui.is_public }}        # Boolean
{{ portal_ui.is_portal }}        # Boolean
{{ portal_ui.is_staff }}         # Boolean
{{ portal_ui.is_superadmin }}    # Boolean
{{ portal_ui.navigation }}       # Filtered navigation items for current context
{{ portal_ui.nav_sections }}     # Navigation grouped by section
{{ portal_ui.login_url }}        # Login URL
{{ portal_ui.portal_prefix }}    # Portal URL prefix
{{ portal_ui.staff_prefix }}     # Staff URL prefix
{{ portal_ui.superadmin_prefix }} # Superadmin URL prefix
```

## URL Configuration Example

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # Public website
    path('', include('myapp.public_urls')),

    # Customer portal
    path('portal/', include('myapp.portal_urls', namespace='portal')),

    # Staff portal
    path('staff/', include('myapp.staff_urls', namespace='staff')),

    # Superadmin
    path('superadmin/', include('django_superadmin.urls', namespace='superadmin')),

    # Authentication
    path('accounts/', include('django.contrib.auth.urls')),
]
```

## Integration with Other Packages

django-portal-ui is designed to work with other django-* packages:

- **django-appointments**: Staff appointment forms extend `base_staff.html`
- **django-store**: Customer orders extend `base_portal.html`
- **django-superadmin**: Admin panels extend `base_superadmin.html`

Each package's templates automatically get the correct navigation and styling.

## Requirements

- Python 3.10+
- Django 4.2+

## Frontend Dependencies

The base templates include CDN links for:
- Tailwind CSS 3.x
- Alpine.js 3.x

For production, consider bundling these locally.

## License

Copyright 2025 Nestor Wheelock. All Rights Reserved.
