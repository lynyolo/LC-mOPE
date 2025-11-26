# 说明
本项目为论文：**《基于临时缓存表的高效保序加密方案设计》**的代码实现(Order-Preserving Encryption)。
该代码主要用于复现论文中的加密逻辑，以进行加密时间统计和单次加密平均通信次数统计。  
查询相关函数（如 `query_message()` 和 `range_query_message()`）仍处于开发中，尚未完全实现，具体说明见源码注释和 README 的相关说明。

# 运行前参数修改
1. **切换数据库**(server/db/config/db_config: 'database': '')、**切换表**(server/encoding_transformer_utils.py: selected_table=)  
2. 通过client/encryption/encryption_scheme.py**切换加密算法**，已实现的加密算法包括AES、SM4、FPE(FF1_AES、FF1_SM4)，其中FF1_AES/FF1_SM4通过fpe.py切换
3. 分别运行Client.py和Server.py：
+ python -m server.Server
+ python -m client.Client
4. Client.py运行后进行数据插入：`/insert file:dataset.txt`

# 客户端可进行的数据操作
1、insert
- 直接插入
- 文件插入：/insert file: insert_test.txt

2、query和range_query  
!! 需要注意的是当前版本的client/Client.py中的query_message()函数和range_message()函数尚未完全实现，运行时会产生错误。

所提到的函数**并未用于**论文中实验结果的获取，只用于保序加密的功能说明，实际的基于客户端临时缓存表的查询逻辑尚未实现。


如有需要，可根据自身需求，使用客户端本地缓存表来自行实现查询功能。
