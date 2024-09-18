import asyncio


class AsyncClient:
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        """连接到服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            print(f"已与IP地址为{self.host}，端口号为{self.port}的服务端建立连接")
        except ConnectionRefusedError as e:
            if e.winerror == 1225:
                print(
                    f"[WinError 1225] {e.strerror}可能的原因："
                    "\n其一，服务端未启动"
                    "\n其二，服务端已由用户指令终止服务"
                    "\n其它一般性网络问题和错误配置"
                )
            raise ConnectionRefusedError(e.strerror)



    async def sendCommand(self, command):
        """发送命令到服务器并接收响应"""
        if self.writer is None:
            raise ConnectionError(f"客户端未与服务端连接，指令“{command}”未发送。")

        print(f"发送: {command}")
        self.writer.write((command + "\n").encode())
        await self.writer.drain()

        response = await self.reader.readline()
        print(f"响应: {response.decode().strip()}")
        return response.decode().strip()

    # TODO
    async def close(self):
        """关闭客户端连接"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            print("已终止与服务端的连接")
        self.reader = None
        self.writer = None

    async def test(self, commands: list[str]):
        """运行测试客户端的命令"""
        try:
            await self.connect()
            for command in commands:
                await self.sendCommand(command)
        except Exception:
            pass
        finally:
            await self.close()

    async def run(self, command: str):
        try:
            await self.connect()
            await self.sendCommand(command)
        except Exception:
            pass
        finally:
            await self.close()


if __name__ == "__main__":
    commands = [
        r"api load H:\PythonProject\ApiBomber\APIs.json",
        "bombing load",
        "bombing start",

        #"bombing pause"
        #"bombing resume"
        #"bombing stop",
    ]

    client = AsyncClient()

    # 运行客户端任务
    asyncio.run(client.test(commands))
