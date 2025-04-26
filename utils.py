import json
import logging
import time

import requests

BASE_GAME_URL = "https://gs.clickfight.net/"


logger = logging.getLogger("utils.py")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/135.0.0.0 Safari/537.36"
}


class Yeast:
    def __init__(self):
        self.alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
        self.length = len(self.alphabet)
        self.map_ = dict()

        self.seed = 0
        self.i = 0
        self.prev = None

        for k, v in enumerate(self.alphabet):
            self.map_[v] = k

        self.yeast()

    def encode(self, num):
        encoded = ""

        while num > 0:
            encoded = self.alphabet[num % self.length] + encoded
            num = int(num / self.length)

        return encoded

    def decode(self, data):
        decoded = 0
        for i in data:
            decoded = decoded * self.length + self.map_[i]

    def generate_timestamp_param(self):
        ts = self.encode(int(time.time() * 1000))
        logger.info(f"Generated yeast timestamp {ts}")
        return ts

    def yeast(self):
        now = self.encode(int(time.time() * 1000))

        if now != self.prev:
            self.seed = 0
            self.prev = now
            return
        self.seed += 1
        return f"{now}.{self.encode(self.seed)}"


class WebsocketGenerator:
    def __init__(self):
        self.sid: str | None = None
        self.ping_interval: int = 2500
        self.ping_timeout: int = 20000
        self.max_payload = 1000000
        self.yeast = Yeast()

    def _get_sid(self):
        request = requests.get(
            f"{BASE_GAME_URL}socket.io/?EIO=4&transport=polling&t={self.yeast.generate_timestamp_param()}",
            headers=headers
        )

        request.raise_for_status()

        data = json.loads(request.text[1:])
        self.sid = data.get('sid', str)
        self.ping_interval = data.get("pingInterval") or 25000
        self.ping_timeout = data.get("pingTimeout") or 20000
        self.max_payload = data.get("maxPayload") or 1000000

    def _authenticate(self, user_id: int, token: str):
        payload = {
            "userId": user_id,
            "token": token
        }
        payload = f"40{json.dumps(payload)}"

        url = (f"{BASE_GAME_URL}socket.io/?EIO=4&transport=polling&t={self.yeast.generate_timestamp_param()}"
               f"&sid={self.sid}")

        r = requests.post(url, data=payload, headers=headers)

        if r.status_code != 200:
            print(r.text)

        r.raise_for_status()

    def _revalidate_sid(self):
        url = (f"{BASE_GAME_URL}socket.io/?EIO=4&transport=polling&t={self.yeast.generate_timestamp_param()}"
               f"&sid={self.sid}")
        request = requests.get(url, headers=headers)

    def generate(self, user_id: int, auth_token: str):
        i = 0
        while i < 10:
            try:
                self._get_sid()
                self._authenticate(user_id=user_id, token=auth_token)
                break
            except requests.exceptions.HTTPError:
                i += 1
        else:
            logger.info("Couldn't authenticate.")
            exit(0)

        self._revalidate_sid()

        return f"{BASE_GAME_URL.replace('https', 'wss')}socket.io/?EIO=4&transport=websocket&sid={self.sid}"

    @property
    def opts(self):
        return {
            "pingInterval": self.ping_interval,
            "pingTimeout": self.ping_timeout,
            "maxPayload": self.max_payload
        }
