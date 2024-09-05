     # 高并发 API 轰炸服务与客户端
该项目是一个异步 API 服务器。服务器使用 Python 的`asyncio`和`multiprocessing`模块并发处理多个 API 请求。

## 特性

- [X] **高并发**: 超高效率的轰炸！
- [X] **动态配置**: 支持在服务器运行时或轰炸时动态更改服务器配置（如端口、进程数、单进程并发限制、代理）。配置将会在服务器关闭时自动保存到`config.json`。
- [X] **代理**
- [X] **客户端指令**


- [ ] **代理池**
- [ ] **自动指令**

## 开始使用
### 先决条件

确保在您的系统中包含以下运行环境和支持库:

- Python 3.9+

安装依赖库:
```bash
pip install -r requirements.txt
```

### 配置服务端
在`server.py`所在的目录中创建`config.json`文件。   
以下是一个示例配置：

```json
{
    "port": 12345,
    "coroutines_per_process": 5,
    "num_processes": 3,
    "proxy": "http://127.0.0.1:8080"
}
```

### 部署服务端
#### 启动服务器

运行`server.py`即可启动服务端，不过这时还不能使用:
```bash
python server.py
```

#### 加载 API 信息

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

### 客户端
使用`client.py`向服务器发送命令。以下是支持的命令：
* LOAD: 从`.json`加载 API 信息。
    ```bash
    python client.py 127.0.0.1 12345 LOAD api_config.json
    ```
* START: 开始轮番轰炸 API。
    ```bash
    python client.py 127.0.0.1 12345 START
    ```
* STOP: 停止轰炸。
    ```bash
    python client.py 127.0.0.1 12345 STOP
    ```
* SET: 动态调整服务器配置。
    ```bash
    python client.py 127.0.0.1 12345 SET port 8080
    ```

## 注意事项
* 服务器将在关机时把运行时所作的任何配置更改保存到`config.json`。
* 如果更改了端口等关键设置，确保在使用客户端时更改端口号。

## 特别感谢
暂待补充

## 开源许可
该项目开源，采用 MIT 许可。