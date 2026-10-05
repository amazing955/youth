import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_application = get_asgi_application()
from accounts.ws_auth import TokenAuthMiddleware
from accounts.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
	'http': django_application,
	'websocket': TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
