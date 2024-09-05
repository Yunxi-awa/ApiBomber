# High-Concurrency API Bombing Service and Client
This project is an asynchronous API server
that uses Python's asyncio and multiprocessing modules
to handle multiple API requests concurrently.

## Features

- [X] **High Concurrency**: Ultra-efficient API bombing!
- [X] **Dynamic Configuration**: Supports dynamic server configuration changes
(e.g., port, number of processes, concurrency limits per process, proxy) during runtime or bombing.
Changes are automatically saved to config.json when the server shuts down.
- [X] **Proxy Support**
- [X] **Client Commands**


- [ ] **Proxy Pool**
- [ ] **Automated Commands**

## Getting Started
### Prerequisites

Ensure the following runtime environment and libraries are available on your system:

- Python 3.9+

Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuring the Server
Create a `config.json` file in the same directory as `server.py`.  
Below is a sample configuration:
```json
{
    "port": 12345,
    "coroutines_per_process": 5,
    "num_processes": 3,
    "proxy": "http://127.0.0.1:8080"
}
```

### Deploying the Server
#### Starting the Server

Run `server.py` to start the server, but it won't be usable immediately::
```bash
python server.py
```

#### 加载 API 信息

The server expects API configurations to be dynamically loaded using client commands.
Use the client to load API configurations from a `.json` file.  
Example of an API configuration file:
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

### Client
Use `client.py` to send commands to the server. Supported commands include:
* LOAD: Load API information from a `.json` file.
    ```bash
    python client.py 127.0.0.1 12345 LOAD api_config.json
    ```
* START: Start bombing APIs.
    ```bash
    python client.py 127.0.0.1 12345 START
    ```
* STOP: Stop bombing.
    ```bash
    python client.py 127.0.0.1 12345 STOP
    ```
* SET: Dynamically adjust server configuration.
    ```bash
    python client.py 127.0.0.1 12345 SET port 8080
    ```

## Notes
* Any configuration changes made during runtime will be saved to `config.json` when the server shuts down.
* If you change critical settings such as the port, make sure to update the client to use the new port.

## Acknowledgements
To be added.

## License
This project is open-source under the MIT License.