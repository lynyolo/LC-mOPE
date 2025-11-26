from client.encryption.aes_encryption import AESEncryption
from client.encryption.fpe import FPE
from client.encryption.sm4_encryption import SM4Encryption


# Super basic encryption scheme.
class BasicEncryptionScheme:
    def __init__(self, key=None):
        self.key = key if key else AESEncryption.generate_key()
        # 确定性加密算法——AES
        # self.cipher = AESEncryption(self.key)
        # 确定性加密算法——SM4
        # self.cipher = SM4Encryption(self.key)
        # 确定性加密算法——FPE(SM4)
        self.cipher = FPE(self.key)


    def encrypt(self, message):
        # return message
        return self.cipher.encrypt(message)

    def decrypt(self, ciphertext):
        # return ciphertext
        return self.cipher.decrypt(ciphertext)

    def generate_key(self):
        return self.key


if __name__ == '__main__':
    # message = "90313454390"
    # message = "sxdfrgfdgfb"
    message = "hifsaeu89u42"
    # message = "Account1234567890123456"

    encryption_scheme = BasicEncryptionScheme()

    ciphertext = encryption_scheme.encrypt(message)
    print("加密后的消息:", ciphertext)

    plaintext = encryption_scheme.decrypt(ciphertext)
    print("解密后的消息:", plaintext)

    assert message == plaintext, f"ERROR! message != plaintext"