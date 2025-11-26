import uuid


class MessageProtocol:
    def __init__(self):
        self.uuid = uuid.uuid4() # generates a random universally unique ID.

    def __str__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


class ServerMessage(MessageProtocol):
    def __init__(self, ciphertext, client_message, find_node_path=None, query_results=None, message_type="insert"):
        MessageProtocol.__init__(self)
        self.ciphertext = ciphertext
        self.client_message = client_message
        self.find_node_path = find_node_path
        self.message_type = MessageType(message_type) # 设置消息类型，默认为 "insert"
        self.query_results = query_results if query_results is not None else []

    def dict_to_message(self, dict):
        message = ServerMessage()
        for key, value in dict.items():
            setattr(message, key, value)
        return message

    def to_dict(self):
        return {
            'uuid': str(self.uuid),
            'ciphertext': self.ciphertext,
            'client_message': self.client_message,
            'message_type': self.message_type.to_dict() if hasattr(self.message_type, 'to_dict') else str(self.message_type)
        }


class ClientMessage(MessageProtocol):
    def __init__(self):
        MessageProtocol.__init__(self)
        self.message_type = None
        self.ciphertext = None # 当前节点密文
        self.new_ciphertext = None # 待插入密文
        self.insert_direction = None # left/right/none
        self.path = "" # [path]
        self.min_ciphertext = None
        self.max_ciphertext = None

    def move_left(self, ciphertext):
        self.message_type = MessageType("move_left")
        self.ciphertext = ciphertext

    def move_right(self, ciphertext):
        self.message_type = MessageType("move_right")
        self.ciphertext = ciphertext

    def get_root(self):
        self.message_type = MessageType("get_root")


    def insert(self, ciphertext, new_ciphertext, insert_direction, path):
        self.message_type = MessageType("insert")
        self.ciphertext = ciphertext
        self.new_ciphertext = new_ciphertext
        self.insert_direction = insert_direction
        self._check_insert_direction()
        self.path = path

    def query(self, ciphertext):
        self.message_type = MessageType("query")
        self.ciphertext = ciphertext

    def find_node_path(self, ciphertext):
        self.message_type = MessageType("find_node_path")
        self.ciphertext = ciphertext

    def get_common_node(self, cipher_bound):
        self.message_type = MessageType("get_common_node")
        self.ciphertext = cipher_bound

    def range_query(self, min_ciphertext, max_ciphertext):
        self.message_type = MessageType("range_query")
        self.min_ciphertext = min_ciphertext
        self.max_ciphertext = max_ciphertext

    def _check_insert_direction(self):
        if not (self.insert_direction == 'left' or self.insert_direction == 'right' or self.insert_direction == None):
           raise Exception("'%s' is not a valid insert direction" % self.insert_direction)


    def to_dict(self):
        return {
            'uuid': str(self.uuid),
            'message_type': self.message_type.to_dict() if hasattr(self.message_type, 'to_dict') else str(self.message_type),
            'ciphertext': self.ciphertext,
            'new_ciphertext': self.new_ciphertext,
            'insert_direction': self.insert_direction
        }

'''
        client_dict = self.__dict__.copy()
        client_dict["uuid"] = str(self.uuid) # 转换UUID为字符串
        client_dict["message_type"] = self.message_type.to_dict()  # 将 MessageType 转换为字典
        return client_dict
'''


class MessageType:

    def __init__(self, message_type):
        self._message_type = message_type
        self._check_valid_message_type()

    def type(self):
        return self._message_type  # 添加 return 语句

    def __repr__(self):
        return f"MessageType('{self._message_type}')"  # 提供更详细的表示


    def _check_valid_message_type(self):
        if self._message_type not in ["move_left", "move_right", "get_root", "get_node", "insert", "query", "get_common_node", "find_node_path", "range_query"]:
            raise Exception("'%s' is not a valid message type" % self._message_type)

    def to_dict(self):
        return {
            'message_type': self._message_type  # 将属性添加到字典中
        }