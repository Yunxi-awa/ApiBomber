import cmd


class CLI(cmd.Cmd):
    prompt = "> "

    def __init__(self):
        super().__init__()
        # 存储实例
        self.instances = {}

    def add_instance(self, name, instance):
        """添加类实例"""
        self.instances[name] = instance

    def default(self, line):
        """解析输入命令"""
        parts = line.split()
        if len(parts) < 2:
            print("Invalid command.")
            return

        class_name, command = parts[0], parts[1]
        if class_name not in self.instances:
            print(f"No such class instance: {class_name}")
            return

        instance = self.instances[class_name]
        if command == "set" and len(parts) == 4:
            self.set(instance, parts[2], parts[3])
        elif command == "get" and len(parts) == 3:
            self.get(instance, parts[2])
        else:
            self.call(instance, command)

    def call(self, instance, method_name):
        """调用方法"""
        if hasattr(instance, method_name):
            method = getattr(instance, method_name)
            if callable(method):
                method()
            else:
                print(f"{method_name} is not a callable method.")
        else:
            print(f"No such method: {method_name}")

    def set(self, instance, attribute_name, value):
        """设置属性值"""
        if hasattr(instance, attribute_name):
            setattr(instance, attribute_name, value)
            print(f"Attribute {attribute_name} set to {value}.")
        else:
            print(f"No such attribute: {attribute_name}")

    def get(self, instance, attribute_name):
        """获取属性值"""
        if hasattr(instance, attribute_name):
            value = getattr(instance, attribute_name)
            print(f"Attribute {attribute_name} is {value}.")
        else:
            print(f"No such attribute: {attribute_name}")
