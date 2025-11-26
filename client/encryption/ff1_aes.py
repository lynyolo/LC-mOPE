from Crypto.Cipher import AES
import math
from client.encryption.ff1 import FF1, logger
import string


class FF1_AES(FF1):
    def __init__(self, key, tweak=None, radix=10, ):
        super().__init__(key, tweak, radix)
        self.aes = AES.new(key, AES.MODE_ECB)

    def round_function(self, padding, q, d):
        """ 计算--S """
        # 计算--R=PRF(P || Q)，返回的结果为字节字符串bytes类型--b'\x01\x02\x03'
        r = self.aes.encrypt(padding + q) # 此处包括其他地方，最终需要确认变量的类型，字符串/字节

        # 计算--S（字节字符串）
        s = r

        # 根据输出需求，计算需要的额外块的数量
        num_blocks = math.ceil(d / 16) - 1

        # 循环生成额外的块
        for j in range(1, num_blocks + 1):
            # 将R与j转换成的16字节数组进行异或运算，并通过PRF生成新块
            xor_result = self.xor(r, self.number_to_array_of_bytes(j, 16))
            s += self.aes.encrypt(xor_result)

        logger.debug(f"R={r}, s={s}")
        return s # 返回加密后的字节序列


if __name__ == '__main__':
    cipher = FF1_AES.withCustomAlphabet(b'0123456789abcdef', None, string.digits + string.ascii_lowercase + string.ascii_uppercase)
    # message = "90313454390"
    # message = "sxdfrgfdgfb"
    message = "hifsaeu89u42"
    ciphertext = cipher.encrypt(message)
    plaintext = cipher.decrypt(ciphertext)

    logger.debug(f"message: {message}, ciphertext: {ciphertext}, plaintext: {plaintext}")
    assert message == plaintext, f"ERROR! {message} != {plaintext}"
