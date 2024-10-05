# import asyncio
# import copy
# import enum
#
# import aiofiles
# import orjson
# from loguru import logger
#
# from command import CommandSupport
#
# class ConfigClass:
#     def __init__(self, **kwargs):
#         for k, v in kwargs.items():
#             setattr(self, k, v)
#     def __repr__(self):
#         return self.__class__.__name__
#
# class ConfigManager(CommandSupport):
#     default = {
#         "socket": {
#             "host": "localhost",
#             "port": 5914
#         },
#         "request": {
#             "timeout": 3000,
#             "maxRetry": 3,
#             "retryDelay": 1000,
#             "maxRedirects": 3
#         },
#         "performance": {
#             "processes": 8,
#             "concurrency": 64,
#             "jitter": 500
#         },
#         "log": {
#             "level": "info",
#             "path": "./server.log",
#             "rotation": "64 MB",
#             "compression": False
#         }
#     }
#     defaultFilePath: str = ".//ServerConfig.json"
#
#     def __init__(self):
#         self.configsStored: dict[str, dict[str, str]] = {}
#         asyncio.run(self.load(self.defaultFilePath))
#
#     async def load(self, path: str):
#         try:
#             async with aiofiles.open(path, "r", encoding="utf-8") as f:
#                 self.configsStored = orjson.loads(await f.read())
#             return f"{path}中配置信息已加载完成。"
#         except FileNotFoundError:
#             logger.warning(f"未找到{path}文件，将创建一个新文件。")
#             async with aiofiles.open(path, "w", encoding="utf-8") as f:
#                 await f.write(orjson.dumps(
#                     self.default,
#                     option=orjson.OPT_APPEND_NEWLINE|orjson.OPT_INDENT_2)
#                 )
#             self.configsStored = self.default
#             return f"未找到{path}文件，将创建一个新文件并使用默认配置。"
#         except orjson.JSONDecodeError:
#             logger.warning(f"配置文件 “{path}” 解析失败，将使用默认配置。")
#             self.configsStored = self.default
#             return f"配置文件 “{path}” 解析失败，将使用默认配置。"
#
#     def getConfig(self, classification: str, key: str):
#         if classification not in self.configsStored:
#             raise KeyError(f"未找到分类 “{classification}”")
#         if key not in self.configsStored[classification]:
#             raise KeyError(f"未找到键 “{classification}.{key}”")
#         return self.configsStored[classification][key]
#
#
#     def mergeConfig(self):  # TODO
#         stack = [(self.configsStored, self.default, "")]
#
#         while stack:
#             currentUserConfig, currentDefaultConfig, path = stack.pop()
#             for k in list(currentUserConfig.keys()):
#                 if k not in currentDefaultConfig:
#                     logger.warning(
#                         f"配置文件 “{self.defaultFilePath}” 中存在无效键 “{path + k}”，"
#                         f"将会被忽略。"
#                     )
#                     del currentUserConfig[k]
#
#             for k, v in currentDefaultConfig.items():
#                 if k not in currentUserConfig:
#                     logger.warning(
#                         f"配置文件 “{self.defaultFilePath}” 中缺少键 “{path + k}”。"
#                         f"已将其设置为默认值 “{v}”"
#                     )
#                     currentUserConfig[k] = copy.deepcopy(v)
#                 elif isinstance(v, dict):
#                     stack.append((currentUserConfig[k], v, path + k + "."))
#
#     def __getattr__(self, item):
#         return self.configsStored[item]
#
#
# config = ConfigManager()
import asyncio

import aiofiles
import orjson

from src.command import CommandSupport
from src.node import Node


class Config(CommandSupport):
    def __init__(self):
        super().__init__()
        asyncio.run(self.load())

    def __getattr__(self, name):
        if name in ("node", "_attrs"):
            return super().__getattribute__(name)
        elif name in self.node.subNodes:
            return self.node[name]
        raise AttributeError(f"实例 “{self.__class__}” 没有属性 “{name}”。")

    def __setattr__(self, name, value):
        if name in ("node", "_attrs"):
            super().__setattr__(name, value)
        else:
            self.node[name] = Node(name, value)

    async def load(self):
        async with aiofiles.open("./asset/ServerConfig.json", "r", encoding="utf-8") as f:
            self.node = Node.createTree(orjson.loads(await f.read()))

    async def save(self):
        async with aiofiles.open("./asset/ServerConfig.json", "w", encoding="utf-8") as f:
            await f.write(
                orjson.dumps(
                    self.node.value,
                    option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2
                )
            )


config = Config()
