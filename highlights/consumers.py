from channels.generic.websocket import AsyncJsonWebsocketConsumer


class JobProgressConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.group_name = f"job_{self.job_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_update(self, event) -> None:
        await self.send_json(event["payload"])
