import string

from client.encryption.ff1_aes import FF1_AES
from client.encryption.ff1_sm4 import FF1_SM4

# FPE-AES/SM4 (FF1-10轮)
class FPE:
    def __init__(self, key, algorithm="SM4"):
        self.key = key
        self.tweak = None
        self.algorithm = algorithm.upper()
        if self.algorithm not in ["AES", "SM4"]:
            raise ValueError("Unsupported algorithm. Use 'AES' or 'SM4'.")


    def encrypt(self, message):
        alphabet = self.get_alphabet(message)

        if self.algorithm == "AES":
            cipher = FF1_AES.withCustomAlphabet(self.key, self.tweak, alphabet)
        else:
            cipher = FF1_SM4.withCustomAlphabet(self.key, self.tweak, alphabet)

        return cipher.encrypt(message)


    def decrypt(self, ciphertext):
        alphabet = self.get_alphabet(ciphertext)

        if self.algorithm == "AES":
            cipher = FF1_AES.withCustomAlphabet(self.key, self.tweak, alphabet)
        else:
            cipher = FF1_SM4.withCustomAlphabet(self.key, self.tweak, alphabet)

        return cipher.decrypt(ciphertext)


    def get_alphabet(self, message):
        if message.isdigit():
            alphabet = string.digits
        else:
            if any(char.isdigit() for char in message):
                alphabet = string.digits + string.ascii_lowercase + string.ascii_uppercase
            else:
                alphabet = string.ascii_lowercase + string.ascii_uppercase
        return alphabet