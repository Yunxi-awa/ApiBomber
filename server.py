import asyncio
import orjson
from curl_cffi import requests
from typing import Dict, Any, List
import socket
import multiprocessing
import random
import os


class Config:
    DEFAULT_CONFIG = {
        "port": random.randint(10000, 60000),
        "coroutines_per_process": 5,
        "num_processes": 3,
        "proxy": None  # 默认无代理
    }

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.update(orjson.loads(f.read()))
                    print(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
        else:
            self.save_config()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(orjson.dumps(self.config).decode('utf-8'))
                print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def set(self, key: str, value: Any):
        if key in self.config:
            self.config[key] = value
            self.save_config()
            print(f"Configuration '{key}' set to {value}.")
        else:
            print(f"Unknown configuration key: {key}")

    def get(self, key: str):
        return self.config.get(key, None)


class APIRequest:
    def __init__(
            self,
            url: str,
            method: str,
            headers: Dict[str, str],
            data: Dict[str, Any],
            params: Dict[str, str],
            interval: float
    ):
        self.url = url
        self.method = method.upper()
        self.headers = headers
        self.data = data
        self.params = params
        self.interval = interval

    async def execute(self, session):
        json_data = None
        if self.method == "POST" and self.data:
            try:
                json_data = orjson.loads(orjson.dumps(self.data))
            except Exception as e:
                print(f"Error encoding JSON data: {e}")

        try:
            response = await self._send_request(session, json_data)
            print(response.text)
        except Exception as e:
            print(f"Error while executing {self.method} request to {self.url}: {e}")

    async def _send_request(self, session, json_data):
        if self.method == "GET":
            return await session.get(self.url, headers=self.headers, params=self.params)
        elif self.method == "POST":
            return await session.post(self.url, headers=self.headers, json=json_data,
                                      params=self.params) if json_data else await session.post(self.url,
                                                                                               headers=self.headers,
                                                                                               data=self.data,
                                                                                               params=self.params)
        elif self.method == "PUT":
            return await session.put(self.url, headers=self.headers, data=self.data, params=self.params)
        elif self.method == "DELETE":
            return await session.delete(self.url, headers=self.headers, data=self.data, params=self.params)
        elif self.method == "PATCH":
            return await session.patch(self.url, headers=self.headers, data=self.data, params=self.params)
        else:
            raise ValueError(f"Unsupported method: {self.method}")


class APIManager:
    def __init__(self, config: Config):
        self.api_cache = multiprocessing.Manager().dict()
        self.is_running = multiprocessing.Manager().Value('b', True)
        self.config = config

    def load_apis(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            apis = orjson.loads(f.read())

        for api in apis:
            desc = api.get('DESC', 'No description')
            print(f"Loading API: {desc}")
            api_requests = [APIRequest(
                url=req['URL'],
                method=req['METHOD'],
                headers=req.get('HEADERS', {}),
                data=req.get('DATA', {}),
                params=req.get('PARAMS', {}),
                interval=req.get('INTERVAL', 5.0)
            ) for req in api['REQS']]
            self.api_cache[desc] = api_requests

    async def worker(self, queue: asyncio.Queue):
        async with requests.AsyncSession(proxy=self.config.get('proxy')) as session:
            while True:
                api_request = await queue.get()
                await api_request.execute(session)
                if self.is_running.value:
                    asyncio.create_task(self.schedule_request(queue, api_request, api_request.interval))
                queue.task_done()

    async def schedule_request(self, queue: asyncio.Queue, api_request: APIRequest, delay: float):
        await asyncio.sleep(delay)
        if self.is_running.value:
            await queue.put(api_request)

    async def process_tasks(self, coroutines_per_process: int):
        queue: asyncio.Queue = asyncio.Queue()

        for apis in self.api_cache.values():
            for api_request in apis:
                await queue.put(api_request)

        for _ in range(coroutines_per_process):
            asyncio.create_task(self.worker(queue))

        await queue.join()

    def run_server(self, coroutines_per_process: int):
        asyncio.run(self.process_tasks(coroutines_per_process))


class Server:
    def __init__(self, config: Config):
        self.config = config
        self.api_manager = APIManager(config)

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.config.get('port')
        server_socket.bind(('localhost', port))
        server_socket.listen(5)
        print(f"Server listening on port {port}...")

        processes = [multiprocessing.Process(target=self.api_manager.run_server,
                                             args=(self.config.get('coroutines_per_process'),)) for _ in
                     range(self.config.get('num_processes'))]
        for p in processes:
            p.start()

        try:
            while True:
                client_sock, addr = server_socket.accept()
                print(f"Accepted connection from {addr}")
                client_handler = multiprocessing.Process(target=self.handle_client_connection, args=(client_sock,))
                client_handler.start()
        except KeyboardInterrupt:
            self.config.save_config()

    def handle_client_connection(self, client_socket):
        try:
            request = client_socket.recv(1024).decode('utf-8')
            print(f"Received command: {request}")

            if request.startswith("LOAD"):
                _, file_path = request.split(" ")
                self.api_manager.load_apis(file_path)
                client_socket.send(b"APIs loaded successfully.")

            elif request.startswith("START"):
                self.api_manager.is_running.value = True
                client_socket.send(b"Server started.")

            elif request.startswith("STOP"):
                self.api_manager.is_running.value = False
                client_socket.send(b"All API requests stopped.")

            elif request.startswith("SET"):
                _, key, value = request.split(" ")
                self.config.set(key, value)
                client_socket.send(f"Configuration '{key}' set to {value}.".encode('utf-8'))

            else:
                client_socket.send(b"Unknown command.")
        finally:
            client_socket.close()


if __name__ == "__main__":
    config = Config()
    server = Server(config)
    server.start_server()
