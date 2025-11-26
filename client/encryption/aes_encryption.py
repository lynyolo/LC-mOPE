from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import os


class AESEncryption:
    def __init__(self, key):
        # 初始化时生成 AES 密钥
        self.key = key
        # self.iv = b'\xc9?\x7fHc\xa5\x00\x7f\x15gQ\xe5\xb2\xa3\xd3\x8f'  # 16 字节固定 IV
        self.cipher = AES.new(self.key, AES.MODE_ECB)


    def encrypt(self, message):
        # 将字符串message转换为字节类型
        if isinstance(message, str):
            message = message.encode('utf-8')
        ciphertext = self.cipher.encrypt(pad(message, AES.block_size))
        return ciphertext


    def decrypt(self, ciphertext):
        plaintext = unpad(self.cipher.decrypt(ciphertext), AES.block_size)
        return plaintext.decode('utf-8', errors='ignore') # 确保解码过程中处理潜在错误


    @staticmethod
    def get_encryption_key():
        # 动态构建文件路径
        key_file = os.path.join(os.path.dirname(__file__), "encryption_key.bin")
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = os.urandom(16)  # 或其他生成密钥的方法
            with open(key_file, "wb") as f:
                f.write(key)
            return key

    @staticmethod
    def generate_key():
        return AESEncryption.get_encryption_key()
