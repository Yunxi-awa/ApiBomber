<div align="center">

[//]: # (<h1>)

[//]: # (<span style="color: red;">此README已不再适用于新版本, 请等待更新</span>)

[//]: # (</h1>)

# API 轰炸机

[English](README.md) | [简体中文](README.zh_CN.md)

该项目是一个异步 API 轰炸服务器。  
服务器使用`Apscheduler`和`asyncio`模块并发处理多个 API 请求。

</div>

## 特性

- [X] **高并发**: 超高效率的轰炸！
- [X] **动态配置**: 支持在服务器运行时或轰炸时动态更改服务器配置（如端口、进程数、单进程并发限制、代理）。配置将会在服务器关闭时自动保存到
  `config.json`。
- [X] **代理**
- [X] **客户端指令**
- [X] **自动指令**

- [ ] **代理池**

## 开始使用

### 先决条件

确保在您的系统中包含以下运行环境和支持库:

- Python 3.9+

安装依赖库:

```bash
pip install -r requirements.txt
```

### 配置服务端

在`asset`目录中可见`ServerConfig.json`文件。   
以下是一个示例配置：

```json5
{
  "socket": {
    "host": "localhost",
    "port": 5914
  },
  "request": {
    "timeout": 3000,
    "retryTimes": 3,
    "retryInterval": 10000,
    "retryIntervalJitter": 5000,
    "maxRedirects": 3,
    "impersonate": "chrome"
  },
  "scheduler": {
    "workers": 8,
    "intervalJitter": 500
  },
  "log": {
    "level": "INFO",
    "path": "./log/server.log",
    "rotation": "64 MB",
    "compression": "lzma"
  },
  "runtime": {
    "phones": []
  }
}
```

### 部署服务端

#### 启动服务器

运行`server.py`即可启动服务端，不过这时还不能使用:

```bash
python server.py
```

#### 配置 API 信息

服务器希望通过客户端命令动态加载 API 配置。使用客户端从`.json`文件加载 API。  
API 配置文件示例：

```json
[
  {
    "DESC": "Sample API",
    "REQS": [
      {
        "URL": "https://api.example.com/data",
        "METHOD": "GET",
        "HEADERS": {
          "Authorization": "Bearer token"
        },
        "PARAMS": {
          "query": "value"
        },
        "INTERVAL": 5.0
      }
    ]
  }
]
```

### 使用客户端

使用`client.py`向服务器发送命令。命令分为三部分:

```bash
<实例> <方法> <参数1> <参数2> ...
```

默认情况下，可以访问的实例有

1. #### `server`
    * `start`：启动服务器
    * `stop`：停止服务器
2. #### `bombing`
    * `load`：加载轰炸任务
    * `start`：启动轰炸
    * `pause`：暂停轰炸
    * `resume`：恢复轰炸
    * `stop`：停止轰炸
3. #### `api`
    * `load`：加载 API 信息
4. #### `config`
    * `load`：加载配置
    * `save`：保存配置

> [!TIP]
> 所有的实例都默认继承自CommandSupport，所以都支持get和set方法获取实例的成员变量

## 注意事项

* 服务器将在关机时把运行时所作的任何配置更改保存到`config.json`。
* 如果更改了端口等关键设置，确保在使用客户端时更改端口号。

## 特别感谢

暂待补充

## 开源许可

该项目开源，采用 MIT 许可。