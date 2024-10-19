import os


def write_data_to_txt():
    data = [1, 2, 3, 4, 5]  # 这里定义一组数据，你可以随意修改
    file_path = "test.txt"
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            for item in data:
                f.write(str(item) + '\n')
    else:
        with open(file_path, 'a') as f:
            for item in data:
                f.write(str(item) + '\n')


if __name__ == "__main__":
    write_data_to_txt()
