from django.apps import AppConfig


class GeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'generator'

    def ready(self):
        import generator.signals  # noqa: F401 — registers post_delete signal
