import time, queue
import socket, logging
import pickle
import os
from logging.handlers import RotatingFileHandler
from server.db.db_manager import DatabaseManager
from common import protocol
from server.rebalance import rebalance, height, AVL_Node
from server.encoding_transformer_utils import path_to_OPC, OPC_to_path
from server.encoding_transformer_utils import string_to_binary_data, binary_data_to_string
from server.encoding_transformer_utils import get_table_name


class Server:
    def __init__(self, conn, logger):
        self.conn = conn # socket连接
        self.logger = logger
        self.db_manager = DatabaseManager()

        self.root = None
        self.N = 5 # AVL-N

        self.cnt = 0 # 单次插入交互次数
        self.total_cnt = 0 # 截至目前总交互次数
        self.counter = 0 # 插入数据数量
        self.rebalance_time = 0

        self.ope_table = {} # {ciphertext: AVL_Node}：全局数据结构，包括此前数据库中已存在的和新插入的
        self.path_to_node = {} # {path: AVL_Node}：辅助结构，从数据库中恢复树

        self.id_num = self.restore_tree_from_db()


    def restore_tree_from_db(self):
        id_num = 0
        """从数据库中还原树结构"""
        query = f"SELECT insert_num, OPC FROM {get_table_name()}"
        results = self.db_manager.execute_query(query) # 元组列表

        """
        两遍插入
            第一遍：创建根节点。先创建所有节点对象并存储到一个字典 path_to_node 中，不进行实际的树连接。
            第二遍：构建树结构。遍历 path_to_node，根据 path 逐步连接父节点与子节点。
        """
        # 创建所有节点并存储到path_to_node、ope_table中
        for insert_num, OPC in results:
            # print(f'{insert_num}: {OPC}')

            id_num += 1 # 同样明文的id
            # 获取节点路径
            OPC_str = binary_data_to_string(OPC)
            path = OPC_to_path(OPC_str)

            # 避免重复节点
            if path in self.path_to_node:
                self.path_to_node[path].ids.append(id_num)
                self.logger.debug(f"跳过重复节点：insert_num={insert_num}")
                continue

            # 创建新节点，存储路径和节点
            new_node = AVL_Node(insert_num)
            new_node.path = path
            self.path_to_node[path] = new_node
            self.ope_table[insert_num] = new_node

        # print(f'path_to_node:{self.path_to_node}')

        # 按照path构建树结构
        for path, new_node in self.path_to_node.items():
            # root node
            if path == "":
                self.root = new_node
            else:
                # 找到父节点路径(父节点一定存在)
                parent_path = path[:-1]
                parent_node = self.path_to_node[parent_path]

                # 确定插入位置
                if path[-1] == "0":
                    parent_node.left = new_node
                else:
                    parent_node.right = new_node

                new_node.parent = parent_node

        print(f"树结构已还原，树高{height(self.root)}")
        logger.info(self.ope_table)

        return id_num


    def run(self):
        while True:
            try:
                byte_data = self.conn.recv(4096)
                request_message = pickle.loads(byte_data)
                self.logger.debug(f'Received from client : {request_message}')

                if request_message.message_type.__repr__() != protocol.MessageType("insert").__repr__():
                    self.cnt += 1
                else:
                    self.logger.debug(f'insert_operation_interactions_count({request_message.new_ciphertext}): {self.cnt}')
                    self.counter += 1
                    self.total_cnt += self.cnt
                    self.cnt = 0
                    # if self.counter in [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]:
                    if self.counter in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
                        self.logger.info(f'rebalance_taken: {self.rebalance_time}')
                        self.logger.info(f'inserted: {self.counter}, insert_operation_average_interactions_count: {self.total_cnt / self.counter :2f}')

                self.receive(request_message)  # 处理消息

            except queue.Empty:
                # 如果消息队列为空，稍微延时后继续检查
                time.sleep(1)


    def find_node(self, ciphertext):
        if ciphertext in self.ope_table:
            return self.ope_table[ciphertext]
        else:
            return None


    def path_to_find_node(self, path):
        cur_node = self.root
        for ch in path:
            if ch == '0':
                cur_node = cur_node.left
            else:
                cur_node = cur_node.right
        return cur_node


    def get_common_prefix(self, s1, s2):
        min_len = min(len(s1), len(s2))
        for i in range(min_len):
            if s1[i] != s2[i]:
                return s1[:i]
        return s1[:min_len]


    def get_public_ancestor_node(self, path):
        common_path = self.get_common_prefix(path[0], path[1])
        return self.path_to_find_node(common_path)


    def receive(self, client_message):

        if (client_message.message_type.__repr__() == protocol.MessageType("move_left").__repr__()):
            current = self.find_node(client_message.ciphertext)
            left_child = current.left
            if left_child:
                server_message = protocol.ServerMessage(ciphertext=left_child.value, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("move_right").__repr__()):
            current = self.find_node(client_message.ciphertext)
            right_child = current.right
            if right_child:
                server_message = protocol.ServerMessage(ciphertext=right_child.value, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("get_root").__repr__()):
            if not self.root:
                server_message = protocol.ServerMessage(ciphertext=None, client_message=client_message)
            else:
                server_message = protocol.ServerMessage(ciphertext=self.root.value, client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("find_node_path").__repr__()):
            ciphertext = client_message.ciphertext # []
            path = []
            for ct in ciphertext:
                path.append(self.find_node(ct).path)
            server_message = protocol.ServerMessage(ciphertext=client_message.ciphertext,
                                                    client_message=client_message,
                                                    find_node_path=path,
                                                    message_type="find_node_path")

        elif (client_message.message_type.__repr__() == protocol.MessageType("get_common_node").__repr__()):
            ciphertext = client_message.ciphertext # []
            path = []
            for ct in ciphertext:
                path.append(self.find_node(ct).path)

            public_ancestor_node = self.get_public_ancestor_node(path)

            server_message = protocol.ServerMessage(ciphertext=public_ancestor_node.value,
                                                    client_message=client_message,
                                                    find_node_path=public_ancestor_node.path,
                                                    message_type="get_common_node")

        elif (client_message.message_type.__repr__() == protocol.MessageType("get_node").__repr__()):
            node_path = client_message.path

            if node_path == '':
                server_message = protocol.ServerMessage(ciphertext=self.root.value if self.root!=None else None,
                                                        client_message=client_message)
            else:
                cur_node = self.root
                for ch in node_path:
                    if ch == '0':
                        cur_node = cur_node.left
                    else:
                        cur_node = cur_node.right
                server_message = protocol.ServerMessage(ciphertext=cur_node.value,
                                                        client_message=client_message)

        elif (client_message.message_type.__repr__() == protocol.MessageType("insert").__repr__()):
            self.id_num += 1

            # 数据库更新：将client传来的ciphertext、path存到MySQL
            OPC = path_to_OPC(client_message.path)
            update_query = f"INSERT INTO {get_table_name()}(insert_num, OPC) VALUES(%s, %s)"
            update_params = [(client_message.new_ciphertext, string_to_binary_data(OPC))]
            self.db_manager.execute_update(update_query, update_params)  # 数据插入到数据库中

            # 树节点的更新
            if client_message.new_ciphertext == client_message.ciphertext: # 树中已有节点
                node = self.find_node(client_message.ciphertext)
                node.ids.append(self.id_num)

            else: # 新插入节点
                new_node = AVL_Node(client_message.new_ciphertext)
                new_node.path = client_message.path
                new_node.ids.append(self.id_num)

                # root case
                if client_message.ciphertext == None:
                    self.root = new_node
                    self.ope_table[client_message.new_ciphertext] = self.root
                else:
                    node = self.find_node(client_message.ciphertext)
                    new_node.parent = node

                    if (client_message.insert_direction == "left"):
                        node.left = new_node
                    elif (client_message.insert_direction == "right"):
                        node.right = new_node
                    self.ope_table[client_message.new_ciphertext] = new_node

                    start_time = time.perf_counter()

                    # AVL-N rebalance：server维护树的平衡以及编码的更新
                    while node and node.parent:
                        node = rebalance(node.parent, self.db_manager, self.logger, self.N)
                        node = node.parent

                    end_time = time.perf_counter()
                    self.rebalance_time += end_time - start_time

                    self.update_root()

            server_message = protocol.ServerMessage(ciphertext=client_message.new_ciphertext, client_message=client_message)

        # FIXME: Corresponding logic needs fixing. See README and client/Client.py
        # for details on query_message() and range_query_message().
        elif (client_message.message_type.__repr__() == protocol.MessageType("query").__repr__()):
            # 此处默认确定性查询
            query = f"SELECT * FROM {get_table_name()} WHERE insert_num = %s"
            params = (client_message.ciphertext, )
            results = self.db_manager.execute_query(query, params)  # 数据库查询操作

            # 动态获取列名
            column_names = [desc[0] for desc in self.db_manager.cursor.description]

            # 查询结果封装为字典列表
            query_results = [dict(zip(column_names, row)) for row in results]

            server_message = protocol.ServerMessage(ciphertext=client_message.ciphertext,
                                                    client_message=client_message,
                                                    query_results=query_results,
                                                    message_type="query")

        # FIXME: Corresponding logic needs fixing. See README and client/Client.py
        # for details on query_message() and range_query_message().
        elif (client_message.message_type.__repr__() == protocol.MessageType("range_query").__repr__()):
            # 判断是否存在 min_path 和 max_path
            min_node = self.find_node(client_message.min_ciphertext) if client_message.min_ciphertext else None
            min_path = min_node.path if min_node else ""  # 若找不到节点，赋值为空字符串
            min_OPC = path_to_OPC(min_path)

            max_node = self.find_node(client_message.max_ciphertext) if client_message.max_ciphertext else None
            max_path = max_node.path if max_node else ""  # 若找不到节点，赋值为空字符串
            max_OPC = path_to_OPC(max_path)

            self.logger.debug(f"min_OPC={min_OPC}, max_OPC={max_OPC}")
            self.logger.debug(f"param[0]={string_to_binary_data(min_OPC)}, param[1]={string_to_binary_data(max_OPC)}")

            # 根据 min_path和 max_path的存在情况构建查询条件
            query = f"SELECT * FROM {get_table_name()} "
            params = ()

            if min_node and max_node:
                query += "WHERE OPC BETWEEN %s AND %s"
                params = (string_to_binary_data(min_OPC), string_to_binary_data(max_OPC))
            elif min_node:
                query += "WHERE OPC >= %s"
                params = (string_to_binary_data(min_OPC), )
            elif max_node:
                query += "WHERE OPC <= %s"
                params = (string_to_binary_data(max_OPC), )


            self.logger.debug(f"Executing query: {query}, params: {params}")

            # 执行数据库查询操作
            try:
                results = self.db_manager.execute_query(query, params)
                self.logger.info(results)
            except Exception as e:
                self.logger.error(f"Query failed: {e}, query: {query}, params: {params}")
                return "Query execution failed."

            # 检查查询结果是否为空
            if not results:
                self.logger.info("Query returned no results.")
                server_message = protocol.ServerMessage(ciphertext=client_message.ciphertext,
                                                        client_message=client_message,
                                                        query_results=None,
                                                        message_type="range_query")

            else:
                # 动态获取列名
                column_names = [desc[0] for desc in self.db_manager.cursor.description]

                # 查询结果封装为字典列表
                query_results = [dict(zip(column_names, row)) for row in results]

                server_message = protocol.ServerMessage(ciphertext=client_message.ciphertext,
                                                        client_message=client_message,
                                                        query_results=query_results,
                                                        message_type="range_query")


        self.logger.debug(f'Sending to Client: {server_message}')
        self.conn.sendall(pickle.dumps(server_message))
        return server_message

    def update_root(self):
        while (self.root.parent != None):
            self.root = self.root.parent


def setup_logger():
    logger = logging.getLogger('server_logger')
    logger.setLevel(logging.INFO)

    log_file_path = os.path.join(os.path.dirname(__file__), "run.log")

    handler = RotatingFileHandler(filename=log_file_path, maxBytes=10 ** 6, backupCount=1) # 文件大小限制为1MB，最多保留1个备份

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - line %(lineno)d - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S') # datefmt='%Y-%m-%d %I:%M:%S %p'
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def start_server(logger, host='localhost', port=65432):
    """ 若端口被占用，netstat -ano | findstr :65432 --> taskkill /PID ** /F """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(1)
        logger.info('Server is listening...')

        while True:
            try:
                conn, addr = server_socket.accept()
                with conn:
                    logger.info(f"Connected by {addr}")
                    while True:
                        server = Server(conn, logger)
                        logger.info(f"N={server.N}")
                        server.run()

            except ConnectionResetError:
                logger.error(f'{addr}异常断开连接')
                continue
            except KeyboardInterrupt:
                logger.info('服务器关闭')
                break
        server_socket.close()


if __name__ == '__main__':
    logger = setup_logger()
    start_server(logger)