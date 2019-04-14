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

sentinel = -1

vk_token = os.environ["VK_TOKEN"]
user_id = "192282006"
vk_api_base = "https://api.vk.com/method/"

get_server_url = vk_api_base + f"photos.getMessagesUploadServer?v=5.41&peer_id={user_id}&access_token={vk_token}"
save_photo = vk_api_base + f"photos.saveMessagesPhoto?v=5.41&access_token={vk_token}&photo={{}}&server={{}}&hash={{}}"
send_message = vk_api_base + \
               f"messages.send?v=5.41&access_token={vk_token}&user_id={user_id}&attachment=photo{{}}_{{}}"


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

        file_id = uuid.uuid4().hex

        # Пытался сделать без сохранения на диск, с буфером или просто передавать байты, не вышло, API вк просто фото
        # не детектил
        with open(f"images/{file_id}.png", "wb") as outfile:
            outfile.write(qr)

        files = {
            'photo': open(f'images/{file_id}.png', "rb")
        }
        os.remove(f'images/{file_id}.png')

        # Load a photo on the server
        get_url_response = requests.get(get_server_url)
        upload_url = json.loads(get_url_response.text)["response"]["upload_url"]
        response = requests.post(upload_url, files=files)

        # Save the photo on the server
        json_response = json.loads(response.text)
        photo = json_response["photo"]
        server = json_response["server"]
        photo_hash = json_response["hash"]
        save_photo_url = save_photo.format(photo, server, photo_hash)
        response = requests.get(save_photo_url)

        # Send the photo to user
        json_response = json.loads(response.text)["response"][0]
        owner_id = json_response["owner_id"]
        media_id = json_response["id"]
        send_message_url = send_message.format(owner_id, media_id)
        requests.get(send_message_url)

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
