import asyncio
import atexit
import sys
from asyncio import Server, StreamReader, StreamWriter, CancelledError

import aiofiles
import orjson
from loguru import logger

from src.api import Api
from src.schedule import Scheduler, Task
from src.command import CommandSupport
from src.config import config


class AsyncServer(CommandSupport):
    def __init__(self):
        super().__init__()

        self.server: Server = None
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
                return instance.get(attribute)
            case "set":  # 处理 set 命令
                if len(parts) != 4:
                    return "错误的指令格式。请使用：“<目标实例> set <属性名称> <值类型> <值>”。"
                attribute, typeName, value = parts[2], parts[3], parts[4]
                return instance.set(attribute, typeName, value)
            case _:  # 其他方法调用
                return await instance.call(methodName, *parts[2:])

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

    @property
    async def isPortOccupied(self) -> bool:
        """
        异步检查端口是否被占用
        :return: 如果端口被占用，返回 True；否则返回 False
        """
        try:
            # 创建一个异步的 socket 绑定到 IP:Port
            server = await asyncio.start_server(
                lambda r, w: None,
                config.socket.host.value,
                config.socket.port.value
            )
            server.close()  # 如果绑定成功，说明端口未被占用，关闭server
            await server.wait_closed()
            return False
        except OSError:
            # 如果 OSError 发生，说明端口已经被占用
            return True

    async def start(self):
        """启动异步服务器"""
        if await self.isPortOccupied:
            return (
                f"“[{config.socket.host.value}]:"
                f"{config.socket.port.value}” "
                f"被占用，请关闭其他程序或更换端口。"
            )

        self.server = await asyncio.start_server(
            self.handleClient,
            config.socket.host.value,
            config.socket.port.value
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


class Bombing(CommandSupport):
    def __init__(self, apiMgr: "ApiManager"):
        super().__init__()
        self.scheduler = Scheduler(numberOfWorkers=config.scheduler.workers.value)
        self.apiMgr = apiMgr

    async def load(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"

        for k, v in self.apiMgr.apisStored.items():
            task = Task(
                name=k,
                func=v.run,
                trigger="interval",
                triggerKwargs={"seconds": v.interval, "jitter": 5}
            )
            self.scheduler.addTask(task)
        logger.info("已加载所有API任务。")

        return "轰炸任务已加载。"

    async def start(self):
        if len(config.runtime.phones) == 0:
            return "请先加载手机号码。"
        self.scheduler.start()
        return "已通知调度器。"

    async def pause(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        self.scheduler.pause()
        return "轰炸任务已暂停。"

    async def resume(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        self.scheduler.resume()
        return "轰炸任务已恢复。"

    async def stop(self):
        if len(self.apiMgr.apisStored) == 0:
            return "请先加载API信息。"
        self.scheduler.stop()
        return "轰炸任务已停止并清除。"


class ApiManager(CommandSupport):
    def __init__(self):
        super().__init__()
        self.apisStored: dict[str, Api] = {}

    async def load(self, path: str):
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = orjson.loads(await f.read())
        except FileNotFoundError:
            return f"文件路徑 “{path}” 指向的文件不存在。"
        for group in data:
            api = Api.fromDict(group)
            if api.desc in self.apisStored.keys():
                continue
            self.apisStored[api.desc] = api
        return f"文件路徑 “{path}” 指向的文件中的API信息已加载完成。"


if __name__ == "__main__":
    @atexit.register
    def exitCallback():
        asyncio.run(config.save())
        logger.info("服务端已终止运行。")


    logger.add(
        config.log.path.value,
        rotation=config.log.rotation.value,
        backtrace=True,
        diagnose=True,
        level=config.log.level.value,
        compression=config.log.compression.value,
    )

    s = AsyncServer()
    api = ApiManager()
    b = Bombing(api)

    s.addInstance("api", api)
    s.addInstance("server", s)
    s.addInstance("config", config)
    s.addInstance("bombing", b)

    try:
        asyncio.run(s.start())
    except KeyboardInterrupt:
        logger.info("服务端已因用户行为 “Ctrl-C” 终止。")
