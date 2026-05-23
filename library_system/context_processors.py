"""Template context: site name and fine rate for display in templates."""


def library_globals(request):
    from django.conf import settings

    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Digital Library Management System"),
        "FINE_PER_DAY": getattr(settings, "FINE_PER_DAY", 5),
    }
