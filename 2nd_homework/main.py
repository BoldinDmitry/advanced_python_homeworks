from multiprocessing import Process, Queue
import qrcode
import uuid
import base64
from io import BytesIO
from jinja2 import Template
import imgkit
import os
import requests
import json
import time
from abc import abstractmethod

sentinel = ...


class BaseVKRequest:
    VK_TOKEN = os.environ["VK_TOKEN"]
    USER_ID = "192282006"
    VK_API_BASE = "https://api.vk.com/method/"
    VK_API_METHOD = None
    HTTP_METHOD = None

    def get_url(self):
        return self.VK_API_BASE + self.VK_API_METHOD

    def get_and_parse_response(self):
        response = self.HTTP_METHOD(self.get_url(), self.get_params())
        loaded_json = json.loads(response.text)

        if 'error' in loaded_json or response.status_code != 200:
            raise ValueError(f'Error detected\nURL:{self.get_and_parse_response()}\nPARAMS:{self.get_params()}')

        return loaded_json

    @abstractmethod
    def get_params(self):
        return {}


class UploadServer(BaseVKRequest):
    VK_API_METHOD = 'photos.getMessagesUploadServer'

    def __init__(self):
        self.HTTP_METHOD = requests.get

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.VK_TOKEN,
            'peer_id': self.USER_ID,
        }

    def get(self):
        return super().get_and_parse_response()


class Image(BaseVKRequest):
    VK_API_METHOD = 'photos.saveMessagesPhoto'

    def __init__(self, photo, server, photo_hash):
        self.HTTP_METHOD = requests.get
        self.photo = photo
        self.server = server
        self.hash = photo_hash

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.VK_TOKEN,
            'photo': self.photo,
            'server': self.server,
            'hash': self.hash,
        }

    def save(self):
        return super().get_and_parse_response()


class Message(BaseVKRequest):
    VK_API_METHOD = 'messages.send'

    def __init__(self, owner_id, media_id):
        self.HTTP_METHOD = requests.get
        self.owner_id = owner_id
        self.media_id = media_id

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.VK_TOKEN,
            'user_id': self.USER_ID,
            'attachment': f'photo{self.owner_id}_{self.media_id}'
        }

    def send(self):
        return super().get_and_parse_response()


def generate(data, q):
    for item in data:
        if item is sentinel:
            q.put(sentinel)
            continue
        qr_img = qrcode.make(item)
        buffered = BytesIO()
        qr_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        with open("index.html") as template_file:
            template = Template(template_file.read())
            template = template.render(qr_code=img_str)
            img_bytes = imgkit.from_string(template, False)
            img_buffer = BytesIO()
            img_buffer.write(img_bytes)
            img_buffer.seek(0)
            q.put(img_buffer)


def upload(q):
    while True:
        qr = q.get()

        if qr is sentinel:
            break

        # Get url of the server for an image uploading
        upload_server = UploadServer().get()

        files = {
            'photo': ('photo.png', qr, 'image/png', {'Expires': '0'})
        }

        # Load a photo on the server
        upload_url = upload_server["response"]["upload_url"]
        response = requests.post(upload_url, files=files)
        json_response = json.loads(response.text)

        if 'error' in json_response or response.status_code != 200:
            raise ValueError('Error while loading image on server')

        # Save the photo on the server
        photo = json_response["photo"]
        server = json_response["server"]
        photo_hash = json_response["hash"]
        json_response = Image(photo, server, photo_hash).save()

        if 'error' in json_response or response.status_code != 200:
            raise ValueError('Error while saving image on server')

        # Send the photo to user
        json_response = json_response["response"][0]
        owner_id = json_response["owner_id"]
        media_id = json_response["id"]
        Message(owner_id, media_id).send()

        time.sleep(0.5)


if __name__ == '__main__':
    q = Queue()
    data = []
    for i in range(100):
        data += [uuid.uuid4().hex]
    data += [sentinel]

    generator_process = Process(target=generate, args=(data, q))
    process_two = Process(target=upload, args=(q,))

    generator_process.start()
    process_two.start()

    q.close()
    q.join_thread()

    generator_process.join()
    process_two.join()
