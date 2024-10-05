from collections.abc import MutableMapping, Mapping, Sequence
from typing import Iterable, Any


class Node(MutableMapping):
    def __init__(self, name: str, value=None):
        self.name: str = name
        self.subNodes: dict[str, Node] = {}
        self.value: Any = value


    @classmethod
    def createTree(cls, data: dict):
        root: Node = cls("root", data)
        stack = [(root, data)]

        while stack:
            currNode, currData = stack.pop()

            for k, v in currData.items():
                k = str(k)
                if isinstance(v, Mapping):
                    childNode = cls(k, v)
                    currNode.subNodes[k] = childNode
                    stack.append((childNode, v))
                elif isinstance(v, Sequence) and not isinstance(v, str):
                    childNode = cls(k, v)
                    currNode.subNodes[k] = childNode
                    stack.append((childNode, dict(enumerate(v))))
                else:
                    currNode.subNodes[k] = cls(k, v)

        return root

    def __getitem__(self, name: str):
        return self.subNodes[name]

    def __setitem__(self, name: str, value: Any):
        self.subNodes[name] = Node(name, value)

    def __delitem__(self, name: str):
        del self.subNodes[name]

    def __iter__(self) -> Iterable:
        return iter(self.subNodes)

    def __len__(self) -> int:
        return len(self.subNodes)

    def __getattr__(self, name: str) -> Any:
        if name in self.subNodes:
            return self.subNodes[name]
        raise AttributeError(f"節點 “{name}” 不存在于其父節點 “{self.name}”。")

    def __setattr__(self, name: str, value):
        if name in ("name", "subNodes", "value"):
            super().__setattr__(name, value)
        else:
            self.subNodes[name] = Node(name, value)

    def __delattr__(self, name):
        del self.subNodes[name]

    def getChildNodeByPath(self, path: str) -> "Node":
        """
        根據路徑字符串獲取子節點
        :param path: 路徑字符串
        :return: JsonNode 對象
        """
        nodes = path.split('.')
        node = self
        for part in nodes:
            try:
                node = node.subNodes[part]
            except KeyError:
                raise AttributeError(f"節點 “{part}” 不存在。")
        return node

    def __repr__(self):
        return str(self.value)


def test():
    # if __name__ == "__main__":
    n = Node.createTree({
        "a": "This is A.",
        "b": {
            "c": "This is C.",
            "d": "This is D."
        },
        "e": [
            "This is E.",
            "This is F.",
            {
                "g": "This is G.",
                "h": "This is H."
            }
        ]
    })
    print(n.subNodes)
    print(n.e.subNodes)
    print(n.e[0].value)
    print(n.getChildNodeByPath("a").value)
    print(n.getChildNodeByPath("e.0").value)
    print(n.getChildNodeByPath("e.2.g").value)

    print(n.value)
