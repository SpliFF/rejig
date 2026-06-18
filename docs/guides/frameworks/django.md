# Django Support

Rejig provides specialized tools for refactoring Django projects: managing settings, URLs, apps, and dependencies.

## Installation

```bash
pip install rejig[django]
```

## DjangoProject

The `DjangoProject` class provides Django-specific operations.

`DjangoProject` expects the project root to contain a Django root directory
(named `django-root` by default; override with `django_root_name`).

```python
from rejig.django import DjangoProject

# Use context manager for automatic cleanup
with DjangoProject("/path/to/project") as project:
    # Django-specific operations
    project.add_installed_app("myapp")

# Customize the Django root directory name
with DjangoProject("/path/to/project", django_root_name="src") as project:
    project.add_installed_app("myapp")
```

## Settings Management

### Add to INSTALLED_APPS

```python
with DjangoProject(".") as project:
    # Add app at the end
    project.add_installed_app("myapp")

    # Add after a specific app
    project.add_installed_app("myapp", after_app="django.contrib.auth")
```

### Add Middleware

```python
# Add at the beginning (default position is "first")
project.add_middleware("myapp.middleware.CustomMiddleware")

# Add at specific position
project.add_middleware(
    "myapp.middleware.SecurityMiddleware",
    position="first"  # Before all other middleware
)

# Add at the end
project.add_middleware(
    "myapp.middleware.LoggingMiddleware",
    position="last"
)

# Add after a specific middleware
project.add_middleware(
    "myapp.middleware.LoggingMiddleware",
    position="after",
    after="django.middleware.common.CommonMiddleware"
)
```

### Update Middleware Path

```python
project.update_middleware_path(
    "deprecated.middleware.OldMiddleware",
    "myapp.middleware.NewMiddleware",
)
```

### Manage Settings Variables

```python
# Add a new setting
project.add_setting("MY_SETTING", '"value"')
project.add_setting("CACHE_TIMEOUT", "3600")
project.add_setting("DEBUG_TOOLBAR", "True")

# Add with comment
project.add_setting(
    "API_KEY",
    'os.environ.get("API_KEY")',
    comment="API key from environment"
)

# Update existing setting
project.update_setting("DEBUG", "False")
project.update_setting("ALLOWED_HOSTS", '["*"]')

# Delete setting
project.delete_setting("DEPRECATED_SETTING")
```

## URL Configuration

### Add URL Patterns

```python
with DjangoProject(".") as project:
    # Add a simple URL pattern
    project.add_url_pattern(
        path_str="api/users/",
        view="UserListView.as_view()",
        name="user-list"
    )

    # Add a path with parameters
    project.add_url_pattern(
        path_str="api/users/<int:pk>/",
        view="UserDetailView.as_view()",
        name="user-detail"
    )
```

### Add URL Include

```python
# Include another URLconf
project.add_url_include("api.urls", path_prefix="api/")
project.add_url_include("myapp.urls", path_prefix="myapp/")
```

### Remove URL Patterns

```python
# Remove by view name
project.remove_url_pattern_by_view("OldView")

# Remove by matching a regex against the path() line
project.remove_url_pattern(r'.*deprecated.*')
```

### Find and Move URL Patterns

```python
# Find a URL pattern line (searches all urls.py via include() if no file given)
match = project.find_url_pattern(view_name="UserListView")
if match:
    line, file_path = match
    print(f"Found in {file_path}: {line}")

# Move a URL pattern (and its view import) from one urls.py to another
project.move_url_pattern(
    "UserListView",
    source_urls=project.root_urls_path,
    dest_urls=project.django_root / "api" / "urls.py",
)
```

## App Discovery

Find apps and files containing specific code:

```python
with DjangoProject(".") as project:
    # Find which app contains a class
    app_name = project.find_app_containing_class("MyView", filename="views.py")
    print(f"MyView is in app: {app_name}")

    # Find file containing a class
    file_path = project.find_file_containing_class("MyModel")
    print(f"MyModel is in: {file_path}")

    # Find which app matches an arbitrary regex pattern
    app_name = project.find_app_containing_pattern(
        r"class\s+User\b", filename="models.py"
    )
```

## Dependency Management

Manage pyproject.toml dependencies for Django projects:

```python
with DjangoProject(".") as project:
    # Add Django dependency
    project.add_dependency("django", "^4.2.0")

    # Add related packages
    project.add_dependency("django-rest-framework", "^3.14.0")
    project.add_dependency("django-cors-headers", "^4.0.0")

    # Update dependency
    project.update_dependency("django", "^5.0.0")

    # Remove dependency
    project.remove_dependency("django-deprecated-package")
```

## App Creation

Create a new Django app directory with starter files:

```python
with DjangoProject(".") as project:
    project.create_app(
        "newapp",
        files={
            "views.py": "from django.shortcuts import render\n",
            "urls.py": "from django.urls import path\n\nurlpatterns = []\n",
        },
    )

    # Check whether an app exists / get its path
    if project.app_exists("newapp"):
        print(project.get_app_path("newapp"))
```

## Moving Code (rope)

`DjangoProject` delegates rope-based moves to the internal Rejig instance.
These update imports across the project automatically:

```python
with DjangoProject(".") as project:
    project.move_class(
        project.django_root / "myapp" / "views.py",
        "UserListView",
        "myapp.api.views",
    )
    project.move_function(
        project.django_root / "myapp" / "utils.py",
        "helper",
        "myapp.common",
    )
```

## Common Patterns

### Set Up New Django App

```python
with DjangoProject(".") as project:
    app_name = "newapp"

    # Add to INSTALLED_APPS
    project.add_installed_app(app_name)

    # Add URL include
    project.add_url_include(f"{app_name}.urls", path_prefix=f"{app_name}/")

    # Add any required middleware
    if needs_middleware:
        project.add_middleware(f"{app_name}.middleware.CustomMiddleware")
```

### Migrate to Django REST Framework

```python
with DjangoProject(".") as project:
    # Add DRF to dependencies
    project.add_dependency("djangorestframework", "^3.14.0")

    # Add to INSTALLED_APPS
    project.add_installed_app("rest_framework")

    # Add REST framework settings
    project.add_setting("REST_FRAMEWORK", """{
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
    }""")
```

### Update Django Version

```python
with DjangoProject(".") as project:
    # Update dependency
    project.update_dependency("django", "^5.0.0")

    # Update deprecated settings
    project.delete_setting("USE_L10N")  # Removed in Django 4.0

    # Rename a middleware path (if a class moved between versions)
    project.update_middleware_path(
        "django.middleware.csrf.OldCsrfViewMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
    )
```

### Add Authentication App

```python
with DjangoProject(".") as project:
    # Add dependencies
    project.add_dependency("django-allauth", "^0.54.0")

    # Add to INSTALLED_APPS
    for app in [
        "django.contrib.sites",
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
    ]:
        project.add_installed_app(app)

    # Add settings
    project.add_setting("SITE_ID", "1")
    project.add_setting("AUTHENTICATION_BACKENDS", """[
        'django.contrib.auth.backends.ModelBackend',
        'allauth.account.auth_backends.AuthenticationBackend',
    ]""")

    # Add URLs
    project.add_url_include("allauth.urls", path_prefix="accounts/")
```

## Integration with Core Rejig

For CST-level operations (renaming, editing classes/functions), use a `Rejig`
instance scoped at the Django root alongside the Django-specific operations:

```python
from rejig import Rejig
from rejig.django import DjangoProject

with DjangoProject(".") as project:
    # Django-specific operations
    project.add_installed_app("newapp")
    project.add_middleware("myapp.middleware.Custom")

    # Core Rejig operations on the same tree
    rj = Rejig(project.django_root)
    rj.find_class("MyModel").add_method("__str__")
```

## Settings and Path Resolution

`DjangoProject` resolves key paths relative to the Django root. The default
settings file is `django_site/settings/base.py`:

```python
with DjangoProject(".") as project:
    print(f"Project root:  {project.project_root}")
    print(f"Django root:   {project.django_root}")
    print(f"Settings file: {project.settings_path}")
    print(f"Root urls.py:  {project.root_urls_path}")
    print(f"pyproject:     {project.pyproject_path}")
```

Settings operations accept an explicit `settings_file` argument to target a
different settings module:

```python
from pathlib import Path

project.add_setting(
    "DEBUG", "False",
    settings_file=Path("django-root/django_site/settings/production.py"),
)
```
