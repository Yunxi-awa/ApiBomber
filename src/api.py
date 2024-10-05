import asyncio
import random
import time
from asyncio import CancelledError
from functools import lru_cache
from typing import Any
from venv import logger

import orjson
from curl_cffi.requests import Headers, AsyncSession, RequestsError, Response

from src.config import config

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

    async def run(self):
        try:
            session = AsyncSession(
                impersonate=config.request.impersonate.value,
                max_clients=16,
                max_redirects=config.request.maxRedirects.value,
                timeout=config.request.timeout.value / 1000
            )

            errors = []
            for phone in config.runtime.phones.value:
                for req in self.reqs:
                    kwargs = req.toKwargs(phone)
                    try:
                        await self.request(session, **kwargs)
                    except RequestsError:
                        logger.error(f"對於電話號碼 “{phone}” 的任務 “{self.desc}” 失败。")
                        errors.append(str(phone))
                        break

            await session.close()

            if len(errors) == 0:
                return f"任務 “{self.desc}” 執行成功。"
            elif len(errors) == len(config.runtime.phones.value):
                return f"任務 “{self.desc}” 全部執行失败。"
            else:
                return f"任務 “{self.desc}” 部分執行成功。其中 “{"” “".join(errors)}” 執行失敗。"

        except CancelledError:
            logger.info(f"任務 “{self.desc}” 被取消。")
            return f"任務 “{self.desc}” 被取消。"

    async def request(self, session: AsyncSession, *args, **kwargs):
        for i in range(1, config.request.retryTimes.value + 1):
            try:
                response: Response = await session.request(*args, **kwargs)
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(
                        f"任務 “{self.desc}” 第{i}次嘗試失败，"
                        f"状态码：{response.status_code}。"
                        f"详细信息：{response.text}"
                    )
            except RequestsError as e:
                logger.warning(f"任務 “{self.desc}” 第{i}次嘗試失败。详细信息：{e}")

            await asyncio.sleep(
                config.request.retryInterval.value / 1000 +
                random.uniform(
                    config.request.retryIntervalJitter.value / 1000,
                    -config.request.retryIntervalJitter.value / 1000
                )
            )

        raise RequestsError(f"任务 “{self.desc}” 失败。")


class Request:
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
            raise ValueError(f"HTTP Method “{method}” 不受支持。")
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

    @lru_cache(maxsize=16)
    def toKwargs(self, phone: int):
        return {
            "method": self.method,
            "url": self.url,
            "params": self._deeplyReplaceMap(
                self.params, {
                    "PHONE": phone,
                    "TIME_STAMP_S": int(time.time()),
                    "TIME_STAMP_MS": int(time.time() * 1000),
                }
            ),
            "headers": self._deeplyReplaceMap(
                dict(self.headers), {
                    "PHONE": phone,
                    "TIME_STAMP_S": int(time.time()),
                    "TIME_STAMP_MS": int(time.time() * 1000),
                }
            ),
            ("json" if "application/json" in
                       self.headers.get("Content-Type", "")
             else "data"): self._deeplyReplaceMap(
                self._rawData, {
                    "PHONE": phone,
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
