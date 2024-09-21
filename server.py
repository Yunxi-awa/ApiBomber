import asyncio
import atexit
import sys
from asyncio import Server, StreamReader, StreamWriter, CancelledError
from typing import Any

import aiofiles
import orjson

from loguru import logger

from schedule import Scheduler
from api import Api



class CommandSupport:
    async def get(self, name):
        if not hasattr(self, name):
            return f"实例 “{self}” 不包含属性 “{name}”。"
        value = getattr(self, name)
        return f"实例 “{self.__class__}” 的属性 “{name}” 的值为 “{value}”。"

    async def set(self, name: str, value: Any):
        if not hasattr(self, name):
            return f"实例 “{self}” 不包含属性 “{name}”。"
        setattr(self, name, value)
        return f"实例 “{self.__class__}” 的属性 “{name}” 已设置为 “{value}”。"

    async def call(self, name: str, *args, **kwargs):
        method = getattr(self, name)
        if not callable(method):
            return f"“{name}” 不是实例 “{self}” 的方法。"
        try:
            # 判断是否为协程函数，分别调用
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        except TypeError as e:
            if "argument" in str(e):
                return f"调用 “{name}” 方法需要参数。"
            raise TypeError(e.args)


class CommandHandler:
    def __init__(self):
        self.instances: dict[str, CommandSupport] = {}

    def addInstance(self, name: str, instance: CommandSupport):
        """添加类实例到字典"""
        if name.lower() in self.instances:
            raise ValueError(f"实例 “[{name}]{instance}” 已存在。")
        if not issubclass(type(instance), CommandSupport):
            raise ValueError(f"实例 “[{name}]{instance}” 不是 CommandSupport 的子类。")
        self.instances[name.lower()] = instance

    async def parseAndExec(self, command):
        """解析并执行命令"""
        parts = command.split()
        if len(parts) < 2:
            return "错误的指令格式。请使用：“<目标实例> <目标方法>”。"

        className, methodName = parts[0], parts[1]
        instance = self.instances.get(className)
        if not instance:
            return f"未找到目标实例 “{className}”"

        match methodName:
            case "get":  # 处理 get 命令
                if len(parts) != 3:
                    return "错误的指令格式。请使用：“<目标实例> get <属性名称>”。"
                attribute = parts[2]
                return await instance.get(attribute)
            case "set":  # 处理 set 命令
                if len(parts) != 4:
                    return "错误的指令格式。请使用：“<目标实例> set <属性名称> <值>”。"
                attribute, value = parts[2], parts[3]
                return await instance.set(attribute, value)
            case _:  # 其他方法调用
                return await instance.call(methodName, *parts[2:])


class AsyncServer(CommandHandler, CommandSupport):
    def __init__(self):
        super().__init__()
        self.server: Server = None

    async def handleClient(self, reader: StreamReader, writer: StreamWriter):
        """处理客户端连接"""
        while True:
            data = await reader.readline()
            if not data:
                break
            command = data.decode().strip()
            logger.info(f"指令：{command}")
            response = await self.parseAndExec(command)
            writer.write((response + "\n").encode())
            logger.info(f"响应：{response}")
            await writer.drain()

        writer.close()
        await writer.wait_closed()

    async def start(self):
        """启动异步服务器"""
        self.server = await asyncio.start_server(
            self.handleClient, "localhost", 8888
        )
        addr = self.server.sockets[0].getsockname()
        logger.info(f"已在 “[{addr[0]}]:{addr[1]}” 上等待连接。")

        async with self.server:
            try:
                await self.server.serve_forever()
            except CancelledError:
                logger.info("服务器已关闭。")

    async def stop(self):
        if self.server.is_serving():
            self.server.close()
            await self.server.wait_closed()
            logger.info("即将退出程序。")
            sys.exit(-1)
        else:
            logger.info("服务器在此之前已终止。")


class Bombing(CommandSupport, Scheduler):
    def __init__(self, apiMgr: "ApiManager"):
        super().__init__(4)
        self.apiMgr = apiMgr

    async def load(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        self._load(self.apiMgr.apisStored)
        return "轰炸任务已加载。"

    async def start(self):
        super().start()
        return "已通知调度器。"

    async def pause(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        super().pause()
        return "轰炸任务已暂停。"

    async def resume(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        super().resume()
        return "轰炸任务已恢复。"

    async def stop(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        super().stop()
        return "轰炸任务已停止并清除。"


class ApiManager(CommandSupport):
    def __init__(self):
        self.apisStored: dict[str, Api] = {}

    async def load(self, path: str):
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = orjson.loads(await f.read())
        except FileNotFoundError:
            return f"{path}文件不存在。"
        for group in data:
            api = Api.fromDict(group)
            if api.desc in self.apisStored.keys():
                continue
            self.apisStored[api.desc] = api
        return f"{path}中API信息已加载完成。"


class ConfigManager(CommandSupport):
    def __init__(self):
        self.configsStored: dict[str, str | list] = {
            "impersonate": "safari",
            "proxies": [],
            "max_directions": 4,
            "max_retry": 3,
            "request_timeout": 10,
        }

    async def load(self, path: str):
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = orjson.loads(await f.read())
        except FileNotFoundError:
            return f"{path}文件不存在。"
        for k, v in data.items():
            if k in self.configsStored.keys():
                self.configsStored[k] = v
            else:
                raise KeyError(f"未知的配置项：{k}")
        return f"{path}中配置信息已加载完成。"


if __name__ == "__main__":
    @atexit.register
    def exitCallback():
        logger.info("服务端已终止运行。")

    logger.add("server.log", rotation="64 MB", backtrace=True, diagnose=True, level="DEBUG")

    s = AsyncServer()
    api = ApiManager()
    c = ConfigManager()
    b = Bombing(api)

    s.addInstance("api", api)
    s.addInstance("server", s)
    s.addInstance("config", c)
    s.addInstance("bombing", b)

    try:
        asyncio.run(s.start())
    except KeyboardInterrupt:
        logger.info("服务端已因用户行为 “Ctrl-C” 终止。")
