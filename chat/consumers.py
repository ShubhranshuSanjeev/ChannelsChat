import json
from django.contrib.auth import get_user_model
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Message

User = get_user_model()


class ChatConsumer(WebsocketConsumer):
    def __init__(self):
        super().__init__()
        self.room_name = ''
        self.room_group_name = ''
        self.commands = {
            'fetch_messages': self.fetch_messages,
            'new_message': self.new_message
        }

    def fetch_messages(self, data):
        messages = Message.last_10_messages()
        content = {
            'command': 'messages',
            'messages': self.messages_to_json(messages)
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        author_user = User.objects.get(username=author)
        message = Message.objects.create(
            author=author_user,
            content=data['message']
        )
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def messages_to_json(self, messages):
        res = []
        for message in messages:
            res.append(self.message_to_json(message))
        return res

    def message_to_json(self, message):
        return {
            'author': message.author.username,
            'content': message.content,
            'timestamp': str(message.timestamp)
        }

    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        self.commands[data['command']](data)

    def send_chat_message(self, message):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    def send_message(self, message):
        self.send(text_data=json.dumps(message))

    def chat_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))
