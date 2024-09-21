import time
from asyncio import CancelledError
from collections.abc import MutableMapping, MutableSequence, Hashable, Sequence, Set
from functools import lru_cache

from typing import Any

import orjson
from curl_cffi.requests import Headers, AsyncSession, RequestsError

supportiveMethod = ["get", "post", "put", "delete", "patch", "head", "options"]


class Api:
    def __init__(
            self,
            desc: str,
            interval: float,
            reqs: list["Request"]
    ):
        self.desc = desc
        self.interval = interval
        self.reqs: list["Request"] = reqs

    @classmethod
    def fromDict(cls, data: dict):
        return cls(
            data["DESC"],
            data.get("INTERVAL", 60),
            [Request.fromDict(i) for i in data["REQS"]]
        )

    def kwargs(self):
        for i in self.reqs:
            yield i.toKwargs()

    async def request(self):
        async with AsyncSession(
                impersonate="safari",
                max_clients=16,
                max_redirects=4
        ) as session:
            for req in self.reqs:
                try:
                    res = await session.request(**req.toKwargs())
                    if res.status_code == 200:
                        return f"任务 “{self.desc}” 已完成。"
                    else:
                        raise RequestsError(f"任务 “{self.desc}” 失败，状态码：{res.status_code}。详细信息：{res.text}")
                except RequestsError as e:
                    raise RequestsError(f"任务 “{self.desc}” 失败。详细信息：{e}。")
                except CancelledError as e:
                    raise CancelledError(f"任务 “{self.desc}” 已取消。")


class Request:
    """A class to represent an API request."""

    def __init__(
            self,
            method: str,
            url: str,
            params: dict = None,
            headers: Headers = Headers(),
            rawData: any = None,
    ):
        if method.lower() in supportiveMethod:
            self.method = method
        else:
            raise ValueError(f"Method {method} is not supported")
        self.url = url
        self.params = {} if params is None else params
        self.headers = headers
        self._rawData = rawData

    @classmethod
    def fromDict(cls, data: dict):
        return cls(
            data["METHOD"],
            data["URL"],
            data.get("PARAMS"),
            Headers(data.get("HEADERS")),
            data.get("DATA")
        )

    def toKwargs(self):
        if "application/json" in self.headers.get("Content-Type", ""):
            return {
                "method": self.method,
                "url": self.url,
                "params": self._deeplyReplaceMap(
                    self.params, {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                ),
                "headers": self._deeplyReplaceMap(
                    dict(self.headers), {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                ),
                "json": self._deeplyReplaceMap(
                    self._rawData, {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                )
            }
        else:
            return {
                "method": self.method,
                "url": self.url,
                "params": self._deeplyReplaceMap(
                    self.params, {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                ),
                "headers": self._deeplyReplaceMap(
                    dict(self.headers), {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                ),
                "data": self._deeplyReplaceMap(
                    self._rawData, {
                        "PHONE": 13633714310,
                        "TIME_STAMP_S": int(time.time()),
                        "TIME_STAMP_MS": int(time.time() * 1000),
                    }
                )
            }

    def _deeplyReplaceMap(self, data: Any, infoMap: dict):
        for k, v in infoMap.items():
            data = self._deeplyReplace(data, k, v)
        return data

    @staticmethod
    def _deeplyReplace(data: any, old: str, new: Any):
        """
        对于继承自 MutableMapping 和 MutableSequence 的对象,
        其包含的字符串都会被识别并替换,
        且返回的数据与原数据结构不变

        :param data: 继承自 MutableMapping 和 MutableSequence 的对象
        :param old: 被替换字符串
        :param new: 替换字符串
        :return: 替换后的数据
        """
        # stack = [data]
        #
        # while stack:
        #     current = stack.pop()
        #
        #     if isinstance(current, MutableMapping):  # 如果是字典
        #         for key, value in current.items():
        #             if isinstance(value, (MutableMapping, MutableSequence)):
        #                 stack.append(value)  # 继续处理嵌套的字典或列表
        #             elif isinstance(value, str):
        #                 if f"$STR[{old}]$" in value:
        #                     current[key] = value.replace(old, str(new))
        #                 elif f"$INT[{old}]$" == value:
        #                     current[key] = int(new)
        #                 elif f"$BOOL[{old}]$" == value:
        #                     current[key] = bool(new)
        #                 elif f"$FLOAT[{old}]$" == value:
        #                     current[key] = float(new)
        #
        #     elif isinstance(current, MutableSequence):  # 如果是列表
        #         for index, item in enumerate(current):
        #             if isinstance(item, (MutableMapping, MutableSequence)):
        #                 stack.append(item)  # 继续处理嵌套的字典或列表
        #             elif isinstance(item, str):
        #                 if f"$STR[{old}]$" in item:
        #                     current[index] = item.replace(old, str(new))
        #                 elif f"$INT[{old}]$" == item:
        #                     current[index] = int(new)
        #                 elif f"$BOOL[{old}]$" == item:
        #                     current[index] = bool(new)
        #                 elif f"$FLOAT[{old}]$" == item:
        #                     current[index] = float(new)

        stringify: str = orjson.dumps(data).decode()
        stringify = (
            stringify.
            replace(f"$STR[{old}]$", str(new)).
            replace(f"\"$INT[{old}]$\"", str(new)).
            replace(f"\"$BOOL[{old}]$\"", str(new)).
            replace(f"\"$FLOAT[{old}]$\"", str(new))
        )
        return orjson.loads(stringify)

    def __eq__(self, other):
        return (
                self.method == other.method
                and self.url == other.url
                and self.params == other.params
                and self.headers == other.headers
                and self._rawData == other._rawData
        )
