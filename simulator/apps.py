# simulator/apps.py
from django.apps import AppConfig

class SimulatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simulator'

    def ready(self):
        # Імпортуємо сигнали тут, щоб вони були зареєстровані при старті Django
        import simulator.signals
        print("Simulator signals registered.") # Для перевірки в консолі