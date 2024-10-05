import asyncio
import atexit
import logging
import multiprocessing
import random
import sys
from asyncio import CancelledError
from enum import StrEnum
from multiprocessing import Process, Manager, Queue
from typing import Callable

from apscheduler.events import EVENT_JOB_MAX_INSTANCES
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger


class WorkerCmd(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    PAUSE = "pause"
    RESUME = "resume"


class WorkerCommand:
    def __init__(self, command: WorkerCmd, taskName: str | None):
        self.command: WorkerCmd = command
        self.taskName: str = taskName


class Worker(Process):
    def __init__(self, wid: int, tasks: dict[str, "Task"]):
        Process.__init__(self)
        self.wid: int = wid
        self.queue: Queue[WorkerCommand] = Queue(maxsize=64)
        self.tasks: dict[str, "Task"] = tasks

    def _exitCallback(self):
        logger.info(f"“进程-{self.wid}” 已退出。")

    def skipListener(self, event):
        logger.warning(f"任务 “{event.job_id}” 已达到最大实例数，跳过执行。")

    def wrapper(self, task: "Task") -> Callable:
        """
        装饰器，用于在任务执行前后记录日志。
        """

        async def decorator():
            logger.debug(f"任务 “{task.name}” 已开始。")
            try:
                retval = await task.run()
                logger.debug(f"任务 “{task.name}” 已结束，返回值：“{retval}”。")
            except CancelledError:
                logger.debug(f"任务 “{task.name}” 已被取消。")
            except Exception as e:
                logger.warning(f"任务 “{task.name}” 执行出错，错误信息：“{e}”。")

        return decorator

    def _handleAddTask(self, scheduler, taskName):
        task = self.tasks.get(taskName)
        # 添加任务到调度器，设置最大实例数量
        scheduler.add_job(
            func=self.wrapper(task),
            trigger=task.trigger,
            max_instances=task.max_instances,
            id=task.name,
            **task.triggerKwargs
        )
        task.wid = self.wid
        self.tasks[task.name] = task
        logger.info(f"任务 “{taskName}” 已被添加至 “进程-{self.wid}”。")

    def _handleRemoveTask(self, scheduler, taskName):
        if taskName is None:
            scheduler.remove_all_jobs()
        else:
            scheduler.remove_job(taskName)
            logger.info(f"任务 “{taskName}” 已从 “进程-{self.wid}” 中删除。")

    def _handlePauseTask(self, scheduler, taskName):
        if taskName is None:
            scheduler.pause()
        else:
            scheduler.pause_job(taskName)
            logger.info(f"任务 “{taskName}” 已被暂停。")

    def _handleResumeTask(self, scheduler, taskName):
        if taskName is None:
            scheduler.resume()
        else:
            scheduler.resume_job(taskName)
            logger.info(f"任务 “{taskName}” 已被恢复。")

    def run(self):
        async def async_work():
            """
            工作协程的主函数，负责处理调度任务。
            """
            logger.info(f"“进程-{self.wid}” 已启动。")
            scheduler = AsyncIOScheduler()
            scheduler.add_listener(self.skipListener, EVENT_JOB_MAX_INSTANCES)
            scheduler.start()

            matchCmd = {
                WorkerCmd.ADD: self._handleAddTask,
                WorkerCmd.REMOVE: self._handleRemoveTask,
                WorkerCmd.PAUSE: self._handlePauseTask,
                WorkerCmd.RESUME: self._handleResumeTask
            }

            while True:
                # 使用线程池执行器从共享队列中异步获取新任务
                try:
                    cmd = await asyncio.to_thread(self.queue.get)
                except CancelledError:
                    logger.debug(f"“进程-{self.wid}” 的读取句柄协程已被取消，进程将会退出。")
                    sys.exit()

                if cmd.command in matchCmd:
                    matchCmd[cmd.command](scheduler, cmd.taskName)
                else:
                    logger.warning(f"“进程-{self.wid}” 接收到了未知的指令 “{cmd.command}”。")

        logger.add("../log/server.log", backtrace=True, diagnose=True, enqueue=True)
        atexit.register(self._exitCallback)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(async_work())


class Task:
    def __init__(
            self,
            name: str,
            func: Callable,
            funcArgs: tuple = (),
            funcKwargs=None,
            trigger: str = 'interval',
            triggerKwargs=None,
            maxInstances: int = 1
    ):
        """
        初始化一个Task对象.
        :param name: 任务名称.
        :param func: 任务执行的函数.
        :param funcArgs: 函数的参数.
        :param funcKwargs: 函数的关键字参数.
        :param trigger: 触发器类型，默认为 'interval'.
        :param triggerKwargs: 触发器参数，例如 {'seconds': 10}.
        :param maxInstances: 允许的最大实例数量.
        """
        self.name = name
        self.func = func
        self.funcArgs = funcArgs
        self.funcKwargs = funcKwargs or {}
        self.trigger = trigger
        self.triggerKwargs = triggerKwargs or {}
        self.max_instances = maxInstances

        self._wid: int = -1

    @property
    def wid(self):
        if self._wid == -1:
            raise ValueError(f"任务 “{self.name}” 尚未被分配到任何进程。")
        return self._wid

    @wid.setter
    def wid(self, wid: int):
        self._wid = wid

    async def run(self):
        """异步运行任务"""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(*self.funcArgs, **self.funcKwargs)
        else:
            return self.func(*self.funcArgs, **self.funcKwargs)

    def __str__(self):
        return f"Task(name={self.name}, wid={self._wid})"


class Scheduler:
    def __init__(self, numberOfWorkers: int):
        self.memoryManager = Manager()
        self.tasksStored: dict = self.memoryManager.dict()

        self._numberOfWorkers: int = numberOfWorkers
        self.workers: list[Worker] = [Worker(i, self.tasksStored) for i in range(self.numberOfWorkers)]

    @property
    def numberOfWorkers(self):
        return self._numberOfWorkers

    @numberOfWorkers.setter
    def numberOfWorkers(self, numberOfWorkers: int):
        self._numberOfWorkers = numberOfWorkers
        self.stop()
        for task in self.tasksStored.values():
            self.addTask(task)

    def _controlTask(self, name: str, command: WorkerCmd):
        if name in self.tasksStored:
            task = self.tasksStored[name]
            self.workers[task.wid].queue.put(WorkerCommand(
                command=command,
                taskName=name
            ))
        else:
            logger.warning(f"任务 “{name}” 未找到。")

    def addTask(self, newTask: Task):
        if newTask.name in self.tasksStored:
            logger.warning(f"任务 “{newTask.name}” 已存在，将不会重复添加。")
            return
        self.tasksStored[newTask.name] = newTask
        random.choice(self.workers).queue.put(WorkerCommand(
            command=WorkerCmd.ADD,
            taskName=newTask.name
        ))

    def pauseTask(self, name: str):
        self._controlTask(name, WorkerCmd.PAUSE)

    def resumeTask(self, name: str):
        self._controlTask(name, WorkerCmd.RESUME)

    def removeTask(self, name: str):
        """
        根据任务名称删除任务
        :param name: 任务名称
        """
        self._controlTask(name, WorkerCmd.REMOVE)
        self.tasksStored.pop(name, None)

    def _controlAllTask(self, command):
        for w in self.workers:
            w.queue.put(WorkerCommand(command=command, taskName=None))

    def start(self):
        for w in self.workers:
            if w.is_alive():
                logger.warning(f"“进程-{w.wid}” 已经启动，无需重复启动。")
                continue
            w.start()
        logger.info("所有进程已启动。")

    def pause(self):
        self._controlAllTask(WorkerCmd.PAUSE)
        logger.info("所有进程已暂停。")

    def resume(self):
        self._controlAllTask(WorkerCmd.RESUME)
        logger.info("所有进程已恢复。")

    def stop(self):
        for w in self.workers:
            w.terminate()
        self.workers = [Worker(i, self.tasksStored) for i in range(self.numberOfWorkers)]
        logger.info("所有进程已停止。")
        self.tasksStored.clear()
        logger.info("所有任务已从存储中删除。")


# 拦截标准日志库的日志并重定向到 loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取 loguru logger 的级别
        logger.log(record.levelno, record.getMessage())


async def example_task(name):
    print(f"“任务-{name}” 在 “进程-{multiprocessing.current_process}” 中运行。")
    await asyncio.sleep(1)
    print(f"“任务-{name}” 运行完毕。")


async def test():
    s = Scheduler(2)

    for i in range(10):
        task = Task(
            name=f"Task{i}",
            func=example_task,
            funcArgs=(f"Task{i}",),
            triggerKwargs={'seconds': random.randint(3, 10)}
        )
        s.addTask(task)

    s.start()
    await asyncio.sleep(5)

    for i in range(8):
        s.removeTask(f"Task{i}")


if __name__ == '__main__':
    # 将标准日志库的 APScheduler logger 绑定到 loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    # 将 APScheduler 的日志器配置为输出到 loguru
    logging.getLogger('apscheduler').setLevel(logging.CRITICAL)

