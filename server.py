import asyncio
import orjson
from curl_cffi import requests
from typing import Dict, Any, List
import socket
import threading

# 全局缓存API配置
api_cache: dict = {}
# 全局开关变量控制API请求执行状态
is_running: bool = True


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
        # 如果全局开关被关闭，停止执行
        if not is_running:
            return

        # 处理请求数据，将 DATA 转换为 JSON 格式（如果可能）
        json_data = None
        if self.method == "POST" and self.data:
            try:
                json_data = orjson.loads(orjson.dumps(self.data))
            except Exception:
                json_data = None

        # 发送请求
        try:
            if self.method == "GET":
                response = await session.get(self.url, headers=self.headers, params=self.params)
            elif self.method == "POST":
                if json_data:
                    response = await session.post(self.url, headers=self.headers, json=json_data, params=self.params)
                else:
                    response = await session.post(self.url, headers=self.headers, data=self.data, params=self.params)
            elif self.method == "PUT":
                response = await session.put(self.url, headers=self.headers, data=self.data, params=self.params)
            elif self.method == "DELETE":
                response = await session.delete(self.url, headers=self.headers, data=self.data, params=self.params)
            elif self.method == "PATCH":
                response = await session.patch(self.url, headers=self.headers, data=self.data, params=self.params)
            else:
                raise ValueError(f"Unsupported method: {self.method}")

            print(response.text)
        except Exception as e:
            print(f"Error while executing {self.method} request to {self.url}: {e}")


async def worker(queue: asyncio.Queue):
    async with requests.AsyncSession() as session:
        while True:
            api_request = await queue.get()
            await api_request.execute(session)
            # 请求完成后，设定一个计时器，延迟加入队列（如果is_running为True）
            if is_running:
                asyncio.create_task(
                    schedule_request(queue, api_request, api_request.interval)
                )
            queue.task_done()


async def schedule_request(queue: asyncio.Queue, api_request: APIRequest, delay: float):
    await asyncio.sleep(delay)
    if is_running:
        await queue.put(api_request)


async def main():
    queue = asyncio.Queue()

    # 将所有API请求加入队列
    for api_key, apis in api_cache.items():
        for api_request in apis:
            await queue.put(api_request)

    # 启动多个worker协程来处理请求
    for _ in range(5):  # 可调整worker数量
        asyncio.create_task(worker(queue))

    await queue.join()  # 等待队列处理完成


def run_server():
    asyncio.run(main())


def load_apis(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        apis = orjson.loads(f.read())

    # 加载API到全局缓存
    for api in apis:
        desc = api.get('DESC', 'No description')
        print(f"Loading API: {desc}")
        api_requests = []
        for req in api['REQS']:
            api_request = APIRequest(
                url=req['URL'],
                method=req['METHOD'],
                headers=req.get('HEADERS', {}),
                data=req.get('DATA', {}),
                params=req.get('PARAMS', {}),
                interval=req.get('INTERVAL', 60.0)  # 默认间隔为5秒
            )
            api_requests.append(api_request)
        api_cache[desc] = api_requests


def handle_client_connection(client_socket):
    global is_running  # 声明使用全局变量
    try:
        request = client_socket.recv(1024).decode('utf-8')
        print(f"Received command: {request}")

        if request.startswith("LOAD"):
            _, file_path = request.split(" ")
            load_apis(file_path)
            client_socket.send(b"APIs loaded successfully.")

        elif request.startswith("START"):
            # 重新启用所有请求的执行
            is_running = True
            threading.Thread(target=run_server).start()
            client_socket.send(b"Server started.")

        elif request.startswith("STOP"):
            # 设置全局开关为 False，停止所有请求
            is_running = False
            client_socket.send(b"All API requests stopped.")

        else:
            client_socket.send(b"Unknown command.")
    finally:
        client_socket.close()


def start_server_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 9999))
    server_socket.listen(5)
    print("Server listening on port 9999...")

    while True:
        client_sock, addr = server_socket.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client_connection, args=(client_sock,))
        client_handler.start()


if __name__ == "__main__":
    start_server_socket()
