# Django Support

Rejig provides specialized tools for refactoring Django projects: managing settings, URLs, apps, models, and views.

## Installation

```bash
pip install rejig[django]
```

## DjangoProject

The `DjangoProject` class provides Django-specific operations.

```python
from rejig.frameworks.django import DjangoProject

# Use context manager for automatic cleanup
with DjangoProject("/path/to/project") as project:
    # Django-specific operations
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

    # Add before a specific app
    project.add_installed_app("myapp", before_app="django.contrib.staticfiles")

    # Add at the beginning (after django apps)
    project.add_installed_app("myapp", position="first")
```

### Remove from INSTALLED_APPS

```python
project.remove_installed_app("deprecated_app")
```

### Add Middleware

```python
# Add at the end
project.add_middleware("myapp.middleware.CustomMiddleware")

# Add at specific position
project.add_middleware(
    "myapp.middleware.SecurityMiddleware",
    position="first"  # Before all other middleware
)

project.add_middleware(
    "myapp.middleware.LoggingMiddleware",
    after="django.middleware.common.CommonMiddleware"
)
```

### Remove Middleware

```python
project.remove_middleware("deprecated.middleware.OldMiddleware")
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

### Read Settings

```python
# Get setting value
debug = project.get_setting("DEBUG")
allowed_hosts = project.get_setting("ALLOWED_HOSTS")

# Check if setting exists
if project.has_setting("MY_CUSTOM_SETTING"):
    value = project.get_setting("MY_CUSTOM_SETTING")
```

## URL Configuration

### Add URL Patterns

```python
with DjangoProject(".") as project:
    # Add a simple URL pattern
    project.add_url_pattern(
        path="api/users/",
        view="UserListView.as_view()",
        name="user-list"
    )

    # Add with regex (for path with parameters)
    project.add_url_pattern(
        path="api/users/<int:pk>/",
        view="UserDetailView.as_view()",
        name="user-detail"
    )
```

### Add URL Include

```python
# Include another URLconf
project.add_url_include("api.urls", path_prefix="api/")
project.add_url_include("myapp.urls", path_prefix="myapp/")

# Include with namespace
project.add_url_include(
    "myapp.urls",
    path_prefix="myapp/",
    namespace="myapp"
)
```

### Remove URL Patterns

```python
# Remove by view name
project.remove_url_pattern_by_view("OldView")

# Remove by path
project.remove_url_pattern_by_path("deprecated/")

# Remove by name
project.remove_url_pattern_by_name("old-endpoint")
```

### Modify URL Patterns

```python
# Update path
project.update_url_path("user-list", "api/v2/users/")

# Update view
project.update_url_view("user-list", "UserListViewV2.as_view()")
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

    # Find app by model
    app_name = project.find_app_containing_model("User")
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

## Model Operations

Work with Django models:

```python
with DjangoProject(".") as project:
    # Find a model
    model = project.find_model("User")

    # Add field to model
    model.add_field("email_verified", "models.BooleanField(default=False)")

    # Remove field
    model.remove_field("deprecated_field")

    # Add method to model
    model.add_method("get_full_name", """
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    """)

    # Add Meta option
    model.add_meta_option("ordering", '["-created_at"]')
```

## View Operations

Work with Django views:

```python
with DjangoProject(".") as project:
    # Find a view class
    view = project.find_view("UserListView")

    # Change base class
    view.change_base_class("ListView", "CustomListView")

    # Add mixin
    view.add_mixin("LoginRequiredMixin")

    # Add attribute
    view.add_attribute("paginate_by", "25")

    # Add method
    view.add_method("get_queryset", """
    def get_queryset(self):
        return super().get_queryset().filter(active=True)
    """)
```

## Migration Helpers

```python
with DjangoProject(".") as project:
    # Generate migration name suggestion
    migration_name = project.suggest_migration_name("myapp")

    # Find migrations that need squashing
    migrations = project.find_migrations_to_squash("myapp", threshold=20)
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

    # Update middleware (if using old names)
    project.remove_middleware("django.middleware.csrf.CsrfViewMiddleware")
    project.add_middleware("django.middleware.csrf.CsrfViewMiddleware")
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

DjangoProject extends the core Rejig functionality:

```python
with DjangoProject(".") as project:
    # All core Rejig operations work
    project.find_class("MyModel").add_method("__str__", ...)
    project.find_function("helper").rename("utility")

    # Plus Django-specific operations
    project.add_installed_app("newapp")
    project.add_middleware("myapp.middleware.Custom")
```

## Settings File Detection

DjangoProject automatically finds your settings file:

```python
with DjangoProject(".") as project:
    # Automatically detects settings from:
    # - DJANGO_SETTINGS_MODULE environment variable
    # - config/settings.py, config/settings/base.py
    # - project_name/settings.py
    # - settings.py

    print(f"Settings file: {project.settings_file}")
```

You can also specify explicitly:

```python
project = DjangoProject(".", settings_module="config.settings.production")
```
