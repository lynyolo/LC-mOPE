import sys
import os
import time
import random
import socket, logging
import pickle
from logging.handlers import RotatingFileHandler
from common import protocol
import client.encryption.encryption_scheme as encryption
from itertools import islice
import traceback
from skip_list import skipList


class Client:
    def __init__(self, client_socket, logger):
        self.encryption_scheme = encryption.BasicEncryptionScheme()
        self.client_socket = client_socket
        self.logger = logger
        self.cache = skipList(logger)
        self.lookup_cache_time = 0


    # ================================================================
    # WARNING:
    # query_message() is NOT fully implemented and will cause errors.
    # The current version only demonstrates the message flow and
    # DOES NOT include the actual query logic.
    #
    # Users may implement their own query mechanism based on a
    # client-side cache table (as described in the README and in the paper: "基于临时缓存表的保序加密方案设计").
    #
    # This function is NOT used in the published paper's experiments.
    # ================================================================
    def query_message(self, message):
        ciphertext = self.encryption_scheme.encrypt(message)
        client_message = protocol.ClientMessage()
        client_message.query(ciphertext)
        return self._send_client_message(client_message)

    # ================================================================
    # WARNING:
    # The range_query_message() function is incomplete and may produce
    # incorrect results. The current implementation of range query
    # logic (including _find_min_or_max) has known issues and has not
    # been fully validated.
    #
    # This range query mechanism was NOT used in the experiments
    # reported in the published paper.
    # Only the encryption-time evaluation is stable.
    #
    # Users may implement their own range-query mechanism based on a
    # client-side cache table, as described in the README.
    # ================================================================
    # FIXME: The logic of range_query_message() is incomplete and needs correction.
    def range_query_message(self, min_message=None, max_message=None):
        if min_message:
            if self.query_message(self.encryption_scheme.encrypt(min_message)):
                min_ciphertext = self.encryption_scheme.encrypt(min_message)
            else: # 找到比给定最小值大的已存在的值 作为最小值
                min_ciphertext = self._find_min_or_max(min_message)
        else:
            min_ciphertext = None

        if max_message:
            if self.query_message(self.encryption_scheme.encrypt(max_message)):
                max_ciphertext = self.encryption_scheme.encrypt(max_message)
            else: # 找到比给定最大值小的已存在的值 作为最大值
                max_ciphertext = self._find_min_or_max(max_message)
        else:
            max_ciphertext = None

        client_message = protocol.ClientMessage()
        client_message.range_query(min_ciphertext, max_ciphertext)
        return self._send_client_message(client_message)


    # FIXME: The logic of _find_min_or_max() is incomplete and needs correction.
    def _find_min_or_max(self, m):
        previous_ciphertext = None  # 元组--（current_ciphertext, 下一步移动方向）

        current_ciphertext = self._get_root()
        path = ""

        while True:
            if current_ciphertext == None:
                if previous_ciphertext == None: # root case
                    find_m = None
                else: # 找到的min/max
                    find_m = previous_ciphertext[0]
                return find_m

            elif m < current_ciphertext:
                # Move left
                path += "0"
                enc_current = self.encryption_scheme.encrypt(current_ciphertext)
                previous_ciphertext = (enc_current, "left")
                current_ciphertext = self._move_left(enc_current)

            elif m > current_ciphertext:
                # Move right
                path += "1"
                enc_current = self.encryption_scheme.encrypt(current_ciphertext)
                previous_ciphertext = (enc_current, "right")
                current_ciphertext = self._move_right(enc_current)

            else: # 实际不存在
                break


    def find_node_path_message(self, message):
        ciphertext = []
        for msg in message:
            ciphertext.append(self.encryption_scheme.encrypt(msg))
        client_message = protocol.ClientMessage()
        client_message.find_node_path(ciphertext)
        return self._send_client_message(client_message)


    def _find_interaction_start_node(self, message):
        '''return path, prompt(提示词）'''
        low_bound, upper_bound = self.cache.search(message)
        self.cache.insert(message)
        if low_bound is None or upper_bound is None:
            return self._get_root(), '', 'root'

        elif low_bound == upper_bound:
            path = self.find_node_path_message([low_bound]) # return []
            return low_bound, path[0], 'insert'
        else:
            current_ciphertext, path = self.get_common_node([low_bound, upper_bound])
            return current_ciphertext, path, 'root'


    def get_common_node(self, bound):
        cipher_bound = []
        for msg in bound:
            cipher_bound.append(self.encryption_scheme.encrypt(msg))
        client_message = protocol.ClientMessage()
        client_message.get_common_node(cipher_bound)
        return self._send_client_message(client_message)


    def insert_message(self, message):
        original_ciphertext = self.encryption_scheme.encrypt(message)
        previous_ciphertext = None # 元组--（current_ciphertext, 下一步移动方向）

        start_time = time.perf_counter()
        current_ciphertext, path, prompt = self._find_interaction_start_node(message) # ！！！假阳性结果:current_ciphertext为初始交互节点
        end_time = time.perf_counter()
        self.lookup_cache_time += end_time - start_time

        if prompt == 'insert': # 数据库中已存在节点
            return self._insert(original_ciphertext, original_ciphertext, self._random_insert_direction(), path)

        while True:
            if current_ciphertext == None: # 空节点
                if path == '':
                    return self._insert(None, original_ciphertext, None, path)
                else: # 找到非根的空插入位
                    if previous_ciphertext[1] == "left":
                        return self._insert(self.encryption_scheme.encrypt(previous_ciphertext[0]), original_ciphertext, "left", path)
                    else:
                        return self._insert(self.encryption_scheme.encrypt(previous_ciphertext[0]), original_ciphertext, "right", path)

            elif message < current_ciphertext:
                # Move left
                path += "0"
                previous_ciphertext = (current_ciphertext, "left")
                enc_current = self.encryption_scheme.encrypt(current_ciphertext)
                current_ciphertext = self._move_left(enc_current)
                if current_ciphertext is not None:
                    self.cache.insert(current_ciphertext)

            elif message > current_ciphertext:
                # Move right
                path += "1"
                previous_ciphertext = (current_ciphertext, "right")
                enc_current = self.encryption_scheme.encrypt(current_ciphertext)
                current_ciphertext = self._move_right(enc_current)

                if current_ciphertext is not None:
                    self.cache.insert(current_ciphertext)

            else: # 已存在节点
                return self._insert(original_ciphertext, original_ciphertext, self._random_insert_direction(), path)


    def _random_insert_direction(self):
        if random.random() > .5:
            return "left"
        else:
            return "right"


    def _get_root(self):
        client_message = protocol.ClientMessage()
        client_message.get_root()
        return self._send_client_message(client_message)


    def _move_left(self, ciphertext):
        client_message = protocol.ClientMessage()
        client_message.move_left(ciphertext)
        return self._send_client_message(client_message)

    def _move_right(self, ciphertext):
        client_message = protocol.ClientMessage()
        client_message.move_right(ciphertext)
        return self._send_client_message(client_message)

    def _insert(self, current_ciphertext, new_ciphertext, direction, path):
        logger.debug("Client insert, current_ciphertext=" + str(current_ciphertext) + ", new_ciphertext:" +
            str(new_ciphertext) + ", direction:" + str(direction) + ", path:" + str(path))
        client_message = protocol.ClientMessage()
        client_message.insert(current_ciphertext, new_ciphertext, direction, path)
        return self._send_client_message(client_message)


    def _send_client_message(self, client_message):
        try:
            logger.debug(f'Sending to Server: {client_message}')
            server_message = pickle.dumps(client_message)
            self.client_socket.sendall(server_message)

            recv_message = self.client_socket.recv(4096)
            recv_data = pickle.loads(recv_message)
            logger.debug(f'Receiving from Server: {recv_data}')

            if recv_data.message_type.__repr__() == protocol.MessageType("insert").__repr__():
                root_ciphertext = recv_data.ciphertext
                if root_ciphertext == None:
                    return None
                else:
                    decrypted_text = self.encryption_scheme.decrypt(root_ciphertext)
                    return decrypted_text

            elif recv_data.message_type.__repr__() == protocol.MessageType("find_node_path").__repr__():
                path = recv_data.find_node_path # []
                return path

            elif recv_data.message_type.__repr__() == protocol.MessageType("get_common_node").__repr__():
                path = recv_data.find_node_path # path
                decrypted_text = self.encryption_scheme.decrypt(recv_data.ciphertext)
                return decrypted_text, path

            elif recv_data.message_type.__repr__() == protocol.MessageType("query").__repr__() or recv_data.message_type.__repr__() == protocol.MessageType("range_query").__repr__():
                if not recv_data.query_results:
                    logger.debug("Query results is empty.")
                    return None

                # 解密查询结果
                decrypted_results = []
                for result in recv_data.query_results:
                    decrypted_record = {} # 字段名为明文，字段值为密文
                    for key, value in result.items():
                        # field_name = self.encryption_scheme.decrypt(self.key, key) if key else None
                        field_name = key
                        # 跳过字段名包含'ope_encoding'的字段的解密
                        if 'OPC' not in key and isinstance(value, bytes):
                            field_value = self.encryption_scheme.decrypt(value) # if value else None
                        else:
                            field_value = value
                        decrypted_record[field_name] = field_value
                    decrypted_results.append(decrypted_record)
                print(decrypted_results)
                return decrypted_results
            else:
                logger.error(f'Unexpected message type: {recv_data.message_type}')
                return None

        except EOFError as eof_err:
            logger.error(f'EOFError: {eof_err}. Connection closed unexpectedly by server')
            sys.exit(1)  # 1 表示程序错误退出，0 表示正常退出
        except pickle.UnpicklingError as unpickle_err:
            logger.error(f'Pickle deserialization error: {unpickle_err}. Invalid data received')
            sys.exit(1)
        except socket.timeout as timeout_err:
            logger.error(f'Socket timeout error: {timeout_err}. Server may be unresponsive')
            sys.exit(1)
        except socket.error as socket_err:
            logger.error(f'Socket error: {socket_err}. Check network or server status')
            sys.exit(1)
        except Exception as general_err:
            logger.error(f'Unexpected error in _send_client_message: {general_err}')
            sys.exit(1)


def setup_logger():
    logger = logging.getLogger('client_logger')
    logger.setLevel(logging.INFO)

    log_file_path = os.path.join(os.path.dirname(__file__), "client.log")

    handler = RotatingFileHandler(filename=log_file_path, maxBytes=10 ** 6, backupCount=1) # 文件大小限制为1MB，最多保留1个备份

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - line %(lineno)d - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S') # datefmt='%Y-%m-%d %I:%M:%S %p'
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def socket_client(logger):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = '127.0.0.1'
    port = 65432  # 必须与服务器端口号一致
    client_socket.connect((ip, port))
    logger.info('Client connected')

    client = Client(client_socket, logger)

    while True:
        msg = input('>>').strip()
        if not msg:
            continue
        handler_message(msg, logger, client)

    client_socket.close()


def handler_message(msg, logger, client):
    # 文件数据必须以/insert file: 形式提供，直接提供数据可以直接输入
    if msg.startswith("/insert"):
        command = "/insert"
        content = msg[len(command):].strip()

        # 检查内容是否为文件路径
        if content.startswith("file:"):
            handler_file_message(content, logger, client)
        else:
            client.insert_message(content)

    elif msg.startswith("/query"):
        command = "/query"
        content = msg[len(command):].strip()
        client.query_message(content)

    elif msg.startswith("/range_query"):  # /range_query 19,54
        command = "/range_query"
        content = msg[len(command):].strip()

        if ',' in content:
            parts = content.split(',')

            # 初始化min_message 和 max_message
            min_message = parts[0].strip() if parts[0].strip() else None
            max_message = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None

            client.range_query_message(min_message, max_message)
        else:
            logger.error("Range query format error. Please enter in format: /range_query min max")

    else:  # 默认插入操作
        logger.debug("No command specified. Defaulting to insert.")
        client.insert_message(msg)


def handler_file_message(content, logger, client):
    file_name = content[5:].strip()
    logger.info(f'insert file:{file_name}')
    file_path = os.path.join(os.getcwd(), "dataset", file_name)  # 正常运行时目录
    # file_path = os.path.join(os.getcwd(), file_name)  # 调试模式下目录
    try:
        start_time = time.time()  # 开始计时
        total_lines = 0  # 插入量统计
        with open(file_path, "r") as f:
            # for line in islice(f, 5000):
            for line in islice(f, 1000):
                data = line.strip()  # 行数据，以空格分割：data_items = line.strip().split(), for data in data_items
                if data:
                    try:
                        logger.debug(f'The {total_lines}th insertion: data: {data}')
                        # logger.handlers[0].flush()  # 强制刷新日志
                        client.insert_message(data)
                        logger.debug(f'Inserted data: {data}')
                        total_lines += 1
                        # if total_lines in [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]:
                        if total_lines in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
                            cur_time = time.time()
                            elapsed_time = cur_time - start_time

                            # 性能统计打印
                            logger.info(f'Total lines inserted: {total_lines}')
                            logger.info(f'Time taken: {elapsed_time:.2f} seconds')
                            logger.info(f'lookup_cache_taken: {client.lookup_cache_time} seconds')
                            logger.info(f"Insertion rate: {total_lines / elapsed_time:.2f} /second")

                    except Exception as e:
                        # 捕获异常并记录完整的堆栈信息
                        logger.error(f'Error during insertion: {e}')
                        logger.error(traceback.format_exc())  # 打印完整的异常堆栈

    except FileNotFoundError:
        logger.error(f'File not found: {file_path}')
    except Exception as e:
        logger.error(f'Error reading file {file_path}: {e}')

if __name__ == '__main__':
    logger = setup_logger()
    socket_client(logger)