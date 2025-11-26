import unittest
import time
from client.encryption.aes_encryption import AESEncryption
from client.encryption.sm4_encryption import SM4Encryption
from client.encryption.fpe import FPE
import os


def timeit(f):
    def timed(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        print(f'func: {f.__name__} took: {te - ts:.4f} seconds.')
        return result
    return timed

class TestEncryptionPerformance(unittest.TestCase):
    def setUp(self):
        """ 初始化测试数据和加密密钥 """
        # self.runs = 10_000
        # self.messages = [
        #     ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        #     for _ in range(self.runs)
        # ]
        self.messages = self.get_message()

        self.key = AESEncryption.get_encryption_key()


    def get_message(self):
        """ 从指定文件中读取数据 """
        file_name = "data_100.txt"
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dataset", file_name)

        try:
            with open(file_path, "r") as f:
                messages = [line.strip() for line in f if line.strip()]
                return messages
        except FileNotFoundError:
            # 如果文件不存在，直接打印错误
            print(f"Error: File not found: {file_path}")
            return []
        except Exception as e:
            # 捕获其他可能的异常并打印
            print(f"Error: An unexpected error occurred while reading the file: {e}")
            return []


    @timeit
    def test_aes_encryption(self):
        cipher = AESEncryption(self.key)
        for message in self.messages:
            cipher.encrypt(message)


    @timeit
    def test_sm4_encryption(self):
        cipher = SM4Encryption(self.key)
        for message in self.messages:
            cipher.encrypt(message)


    @timeit
    def test_ff1_aes_encryption(self):
        cipher = FPE(self.key, "AES")
        for message in self.messages:
            cipher.encrypt(message)


    @timeit
    def test_ff1_sm4_encryption(self):
        cipher = FPE(self.key, "SM4")
        for message in self.messages:
            cipher.encrypt(message)


    @unittest.skip
    def test_print_message(self):
        """ 测试并打印消息内容 """
        print("Message content:")
        print(self.message[:10])  # 打印消息列表
        print(len(self.message))
        self.assertTrue(len(self.message) > 0, "Message list is empty.")  # 确保消息列表非空


if __name__ == '__main__':
    # 运行所有的测试用例
    unittest.main()

    # 运行特定的测试用例
    # suite = unittest.TestSuite()
    # suite.addTest(TestEncryptionPerformance("test_print_message"))  # 添加单个测试
    # runner = unittest.TextTestRunner()
    # runner.run(suite)