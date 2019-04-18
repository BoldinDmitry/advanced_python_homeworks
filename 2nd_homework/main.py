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

sentinel = ...


class BaseVKRequest:
    vk_token = os.environ["VK_TOKEN"]
    user_id = "192282006"
    vk_api_base = "https://api.vk.com/method/"


class GetUploadServer(BaseVKRequest):
    def __init__(self):
        self.URL = self.vk_api_base + 'photos.getMessagesUploadServer'

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.vk_token,
            'peer_id': self.user_id,
        }


class SaveImage(BaseVKRequest):
    def __init__(self, photo, server, photo_hash):
        self.URL = self.vk_api_base + 'photos.saveMessagesPhoto'
        self.photo = photo
        self.server = server
        self.hash = photo_hash

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.vk_token,
            'photo': self.photo,
            'server': self.server,
            'hash': self.hash,
        }


class SendMessage(BaseVKRequest):
    def __init__(self, owner_id, media_id):
        self.URL = self.vk_api_base + 'messages.send'
        self.owner_id = owner_id
        self.media_id = media_id

    def get_params(self):
        return {
            'v': 5.41,
            'access_token': self.vk_token,
            'user_id': self.user_id,
            'attachment': f'photo{self.owner_id}_{self.media_id}'
        }


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
            q.put(img_bytes)


def upload(q):
    requests_count = 0
    old_time = time.time()

    while True:
        qr = q.get()

        if qr is sentinel:
            break

        # Get url of the server for an image uploading
        get_upload_server = GetUploadServer()
        get_url_response = requests.get(get_upload_server.URL, get_upload_server.get_params())
        get_server_response = json.loads(get_url_response.text)

        if 'error' in get_server_response or get_url_response.status_code != 200:
            raise ValueError('Error while getting server url')

        file_id = uuid.uuid4().hex

        with open(f"images/{file_id}.png", "wb") as outfile:
            outfile.write(qr)

        files = {
            'photo': open(f'images/{file_id}.png', "rb")
        }
        os.remove(f'images/{file_id}.png')

        # Пытался отправлять так
        # files = {
        #         'photo': ('photo.png', qr, 'image/png', {'Expires': '0'})
        #     }

        # Load a photo on the server
        upload_url = get_server_response["response"]["upload_url"]
        response = requests.post(upload_url, files=files)
        json_response = json.loads(response.text)

        if 'error' in json_response or response.status_code != 200:
            raise ValueError('Error while loading image on server')

        # Save the photo on the server
        photo = json_response["photo"]
        server = json_response["server"]
        photo_hash = json_response["hash"]
        save_image = SaveImage(photo, server, photo_hash)
        response = requests.get(save_image.URL, save_image.get_params())
        json_response = json.loads(response.text)

        if 'error' in json_response or response.status_code != 200:
            raise ValueError('Error while saving image on server')

        # Send the photo to user
        json_response = json_response["response"][0]
        owner_id = json_response["owner_id"]
        media_id = json_response["id"]
        send_message = SendMessage(owner_id, media_id)
        requests.get(send_message.URL, send_message.get_params())

        if time.time() - old_time >= 1:
            old_time = time.time()
            requests_count = 0
        elif requests_count > 20:
            time.sleep(1 - (time.time() - old_time))
            old_time = time.time()
            requests_count = 0
        else:
            requests_count += 4


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
