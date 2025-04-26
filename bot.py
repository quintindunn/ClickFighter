import json
import logging
import os
import threading
import time

from websocket import WebSocketApp

from utils import WebsocketGenerator

logger = logging.getLogger("bot.py")


class Enemy:
    def __init__(self, e_type: str, e_id: str, name: str, hp: int, max_hp: int, p: int, nc: int, asset: str):
        self.type = e_type  # t
        self.eid = e_id  # id
        self.name = name  # n
        self.hp = hp  # hp
        self.max_hp = max_hp  # mhp
        self.asset = asset  # i
        self.p = p  # p
        self.nc = nc  # nc

    def attack_packet(self):
        return ["p:sa", {"id": self.eid, "type": "npc"}]


class Exploit:
    def __init__(self, p: int, asset: str):
        self.p = p
        self.asset = asset

    def collect_packet(self) -> list:
        return ["expl:col", {"p": self.p}]


class GameStatus:
    def __init__(self, data: dict):
        self.credits: int = int(data.get("credits", -1))
        self.crypto: int = data.get("crypto", -1)
        self.darknet_energy: int = data.get("darknetEnergy", -1)
        self.event_currency: int = data.get("eventCurrency", -1)
        self.level: int = data.get("level", -1)
        self.level_progress: float = data.get("levelProgress", -1)
        self.satoshi: int = int(data.get("satoshi", -1))
        self.user_id = data.get("userId", -1)
        self.xp: int = int(data.get("xp", -1))
        self.xp_till_next_level: int = data.get("xpNextLevel", -1)

    def update(self, data: dict):
        self.credits: int = int(data.get("credits", -1))
        self.crypto: int = data.get("crypto", -1)
        self.darknet_energy: int = data.get("darknetEnergy", -1)
        self.event_currency: int = data.get("eventCurrency", -1)
        self.level: int = data.get("level", -1)
        self.level_progress: float = data.get("levelProgress", -1)
        self.satoshi: int = int(data.get("satoshi", -1))
        self.user_id = data.get("userId", -1)
        self.xp: int = int(data.get("xp", -1))
        self.xp_till_next_level: int = data.get("xpNextLevel", -1)


class Bot:
    def __init__(self, user_id: int, auth_token: str, auto_collect_exploits: bool = False,
                 print_user_log_data: bool = False):
        self.user_id: int = user_id
        self.auth_token: str = auth_token

        ws_generator = WebsocketGenerator()
        self.ws_url = ws_generator.generate(user_id=self.user_id, auth_token=self.auth_token)
        self.opts = ws_generator.opts

        self.enemy_list: list[Enemy] = []
        self.exploits: list[Exploit] = []

        self.msg_log: list[str] = []

        self.status: GameStatus = GameStatus({})

        self.auto_collect_exploits: bool = auto_collect_exploits
        self.print_user_log_data: bool = print_user_log_data

        self.ws = WebSocketApp(url=self.ws_url,
                               on_open=self.on_open,
                               on_message=self.on_message,
                               on_error=self.on_error,
                               on_close=self.on_close)
        self.ws.run_forever()
        self.run_keep_alive = True

    def on_open(self, *_):
        logger.info(f"Websocket opened on url {self.ws_url}!")
        self.ws.send("2probe")

    def on_message(self, _, msg: str):
        self.msg_router(msg)

    @staticmethod
    def on_error(*args, **kwargs):
        logger.error(f"Websocket Error: {args}")

    @staticmethod
    def on_close(*args, **kwargs):
        logger.info("Websocket closed.")

    def start_keep_alive(self):
        self.run_keep_alive = True

        def keep_alive():
            while self.run_keep_alive:
                time.sleep(self.opts["pingInterval"])
                if not self.run_keep_alive:
                    break
                self.send_game_message(["p"])

        thread = threading.Thread(target=keep_alive, daemon=True)
        thread.start()

    def msg_router(self, msg: str):
        if msg == "3probe":
            self.ws.send("5")
            self.send_game_message(["u:ammo:s", 2])
            return
        elif msg == "2":
            self.ws.send("3")
            return

        elif msg[:2] != "42":
            logger.warning(f"Unknown message type! {msg}")
            return

        data = json.loads(msg[2:])

        msg_type = data[0]

        if msg_type == "c:su":
            enemy_data = data[1]

            is_ai_enemy = enemy_data.get("su") is None

            if is_ai_enemy:
                enemy = Enemy(
                    e_type=enemy_data.get("t"),
                    e_id=enemy_data.get("id"),
                    name=enemy_data.get("n"),
                    hp=enemy_data.get("hp"),
                    max_hp=enemy_data.get("mhp"),
                    p=enemy_data.get("p"),
                    nc=enemy_data.get("nc"),
                    asset=enemy_data.get("i")
                )
                self.enemy_list.append(enemy)
                return
        elif msg_type == "expl:spw":
            exploit_data = data[1]
            exploit = Exploit(
                p=exploit_data.get("p"),
                asset=exploit_data.get("i")
            )

            if self.auto_collect_exploits:
                self.send_game_message(exploit.collect_packet())
                return

            self.exploits.append(exploit)
            return
        elif msg_type == "ul:t":
            self.msg_log.append(data[1])

            if self.print_user_log_data:
                logger.info(f"USER_LOG: {self.msg_log[-1]}")
            return

        elif msg_type == "ud:u":
            game_status = data[1]
            self.status.update(game_status)

    def send_game_message(self, data: list):
        self.ws.send(f"42{json.dumps(data)}")

    def send_chat_message(self, msg: str) -> None:
        packet = ["c:m", {"m": msg, "c": 1}]
        self.send_game_message(packet)

    def jump_up(self):
        packet = ["c:jU"]
        self.send_game_message(packet)

    def jump(self):
        packet = ["c:j"]
        self.send_game_message(packet)

    def jump_down(self):
        packet = ["c: jD"]
        self.send_game_message(packet)

    def repair_start(self):
        packet = ["u:rS"]
        self.send_game_message(packet)

    def repair_abort(self):
        packet = ["u:rA"]
        self.send_game_message(packet)


if __name__ == '__main__':
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    bot = Bot(user_id=int(os.getenv("userId")), auth_token=os.getenv("authToken"),
              auto_collect_exploits=True, print_user_log_data=True)
