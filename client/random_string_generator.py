import random
import string
import os


def generate_random_strings(file_path, size, string_length):
    """ 生成指定个数的随机数值型字符串，并保存到指定的txt文件中 """
    with open(file_path, 'w', encoding='utf-8') as file:
        for _ in range(size):
            random_string = ''.join(random.choices(string.digits, k=string_length))
            file.write(random_string + '\n')


if __name__ == "__main__":
    # 设置生成参数
    size = 5000
    string_length = 10
    file_name = f'dataset.txt'
    file_path = os.path.join(os.getcwd(), "dataset", file_name)

    generate_random_strings(file_path, size, string_length)

    print(f'生成{size}个长度为{string_length}的随机字符串，并保存到{file_name}')