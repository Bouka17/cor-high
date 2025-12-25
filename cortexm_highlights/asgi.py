import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortexm_highlights.settings")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import highlights.routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(highlights.routing.websocket_urlpatterns)
        ),
    }
)
