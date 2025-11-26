import mysql.connector

# 数据库连接配置
config = {
    'host': 'localhost',
    'user': 'username',
    'password': 'password'
}

# 数据库列表
databases = ['lc_mope']

# 要新增的表名列表
table_names = ['dataset']

try:
    # 建立数据库连接
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()

    # 遍历数据库列表
    for db in databases:
        cursor.execute(f'use {db}') # 切换到目标数据库

        # 遍历表名列表，创建表
        for table_name in table_names:
            # 表结构定义
            table_structure = (f'CREATE TABLE IF NOT EXISTS {table_name} ('
                               f'id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, '
                               f'insert_num VARBINARY(130) DEFAULT NULL, '
                               f'OPC BINARY(4) NOT NULL'
                               f');')

            create_table_query = table_structure.format(table_name=table_name)
            cursor.execute(create_table_query)

        # 提交更改
        connection.commit()
    print("All changes applied successfully!")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    cursor.close()
    connection.close()

