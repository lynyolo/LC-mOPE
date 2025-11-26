import mysql.connector
from server.db.config.db_config import DATABASE_CONFIG

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def connect(self):
        """建立与数据库的连接"""
        try:
            self.connection = mysql.connector.connect(
                host=DATABASE_CONFIG['host'],
                port=DATABASE_CONFIG['port'],
                user=DATABASE_CONFIG['user'],
                password=DATABASE_CONFIG['password'],
                database=DATABASE_CONFIG['database']
            )
            self.cursor = self.connection.cursor()  # 以列表形式返回查询结果，每个列表元素都是一个(元组)
            print("数据库连接成功")
        except mysql.connector.Error as err:
            print(f"连接数据库失败: {err}")

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("数据库连接已关闭")

    def execute_query(self, query, params=None):
        """执行查询并返回结果"""
        if self.connection == None or self.cursor == None:
            self.connect()  # 确保在执行查询前已连接数据库

        try:
            self.cursor.execute(query, params or ())
            result = self.cursor.fetchall()
            return result

        except mysql.connector.Error as err:
            print(f"查询失败: {err}")
        # finally:
        #     self.close()  # 执行完查询后关闭连接

    def execute_update(self, query, params=None):
        """执行数据更新（如INSERT, UPDATE, DELETE）"""
        if self.connection == None or self.cursor == None:
            self.connect()  # 确保连接数据库

        # 检查 params 是否为 None 或空列表，以避免 executemany 出现错误
        if not params:
            print("警告: params 列表为空，未执行任何操作。")
            return

        try:
            self.cursor.executemany(query, params) # insert时，params为(insert_num, path); update时，params为（path, node.value)
            self.connection.commit()  # 提交更改

        except mysql.connector.Error as err:
            print(f"插入失败: {err}")
        # finally:
        #     self.close()  # 完成后关闭连接
