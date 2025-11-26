selected_table = "dataset" # 默认表名


# path-->OPC
def path_to_OPC(path):
    # 在 path 后添加‘1’，然后填充‘0’直到长度为32位
    OPC = path + '1' + '0' * (32 - len(path) - 1)
    return OPC

# OPC-->path
def OPC_to_path(OPC):
    # 找到最后一个‘1’的位置，返回其之前的子字符串
    last_one_index = OPC.rfind("1")
    path = OPC[:last_one_index]
    return path


# 将 32 位二进制字符串转换为 4 字节数据（用于插入到数据库）
def string_to_binary_data(binary_string):
    # 将二进制字符串转换为整数，然后转换为4字节的二进制数据
    binary_data = int(binary_string, 2).to_bytes(4, byteorder='big')
    return binary_data


# 将 4 字节数据转换为 32 位二进制字符串（用于从数据库读取后）
def binary_data_to_string(binary_data):
    # 将4字节的二进制数据转换为整数，然后转换为32位的二进制字符串
    binary_string = format(int.from_bytes(binary_data, byteorder='big'), '032b')
    return binary_string


def get_table_name():
    return selected_table