import asyncio

import orjson

from src.node import Node


class CommandSupport:
    def __init__(self):
        self._attrs = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }
        self._attrs.update({
            k: v for k, v in self.__class__.__dict__.items()
            if not callable(v) and not k.startswith("_")
        })

        self.node = Node.createTree(self._attrs)

    def get(self, path: str):
        return (
            f"实例 “{self.__class__}” "
            f"的属性 “{path}” "
            f"的值为 “{self.node.getValueByPath(path)}”。"
        )

    def set(self, path: str, typeName: str, value: str):
        if typeName == "str":
            self.node.setValueByPath(path, value)
        else:
            self.node.setValueByPath(path, orjson.loads(value))
        return f"实例 “{self.__class__}” 的属性 “{path}” 已设置为 “{value}”。"

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
