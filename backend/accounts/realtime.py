from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_update(payload, user_id=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    groups = [f'member_updates_{user_id}'] if user_id else []
    groups.append('admin_updates')
    for group in groups:
        async_to_sync(channel_layer.group_send)(group, {'type': 'update.event', 'payload': payload})
