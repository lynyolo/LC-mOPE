from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT


class SM4Encryption:
    def __init__(self, key):
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes long")
        self.key = key
        self.cipher = CryptSM4()
        # self.iv = b'\xc9?\x7fHc\xa5\x00\x7f\x15gQ\xe5\xb2\xa3\xd3\x8f'  # 16 字节固定 IV

    def encrypt(self, message):
        # try:
        self.cipher.set_key(self.key, SM4_ENCRYPT)
        if isinstance(message, str):
            message = message.encode('utf-8')
        ciphertext = self.cipher.crypt_ecb(message)
        return ciphertext
        # except Exception as e:
        #     raise RuntimeError(f"Encrypt error: {e}")


    def decrypt(self, ciphertext):
        # try:
        self.cipher.set_key(self.key, SM4_DECRYPT)
        plaintext = self.cipher.crypt_ecb(ciphertext)
        return plaintext.decode('utf-8', errors='ignore')
        # except Exception as e:
        #     raise RuntimeError(f"Decrypt error: {e}")

if __name__ == '__main__':
    message = "Hello World!"
    cipher = SM4Encryption(b'0123456789abcdef')
    ciphertext = cipher.encrypt(message)
    plaintext = cipher.decrypt(ciphertext)
    print(ciphertext, plaintext)
    assert message == plaintext, f"{message} != {plaintext}"
