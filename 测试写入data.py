
import json

def write_hello_to_json(filename="data.json"):
    """将 "hello" 写入到 JSON 文件.

    如果文件不存在，则创建新文件并将 "hello" 作为第一个元素添加到列表中.
    如果文件存在，则读取现有数据，并将 "hello" 添加到列表末尾.

    Args:
        filename: JSON 文件名.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.append("hello")

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)



if __name__ == "__main__":
    write_hello_to_json()
    print("已将 'hello' 写入 data.json")


