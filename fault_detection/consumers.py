from channels.generic.websocket import AsyncWebsocketConsumer
import json

class HardwareMonitorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("hardware_monitor", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("hardware_monitor", self.channel_name)

    async def hardware_update(self, event):
        message_data = {
            'data': event.get('data'),
            'message': event.get('message'),
            'status': event.get('status')
        }

        message_data = {k: v for k, v in message_data.items() if v is not None}
        await self.send(text_data=json.dumps(message_data))