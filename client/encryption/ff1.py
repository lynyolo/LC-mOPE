from Crypto.Cipher import AES
import math
import string
import logging
from Crypto.Util.number import bytes_to_long


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)

logger.addHandler(console)

class FF1:
    """ Class FF1_AES implements FF1 using AES encryption"""

    # 基于FF1规范的常量
    DOMAIN_MIN = 1_000_000 # 1M required in FF1
    BASE62 = string.digits + string.ascii_lowercase + string.ascii_uppercase
    BASE62_LEN = len(BASE62) # Base62 支持长度最大为62的字母表
    RADIX_MAX = 256

    NUM_ROUNDS = 10
    max_tweak_len = 2 ** 16

    def __init__(self, key, tweak=None, radix=10, ):
        self.key = key
        self.tweak = tweak
        self.aes = AES.new(key, AES.MODE_ECB)

        if not (tweak == None or 2 <= len(tweak) <= self.max_tweak_len):
            raise ValueError(f"tweak length must be between 2 and {self.max_tweak_len}, but got {len(tweak)}")

        # Alphabet depending on radix
        self.radix = radix
        if radix <= FF1.BASE62_LEN:
            self.alphabet = FF1.BASE62[:radix]
        else:
            raise ValueError(f"Radix must be <= {FF1.BASE62_LEN}(base62 limit)")

        # FF1 允许的radix范围：[2, 2^16]，但通常有用的范围是 2..62
        if(radix < 2) or (radix > FF1.RADIX_MAX):
            raise ValueError(f"radix must be between 2 and 62, inclusive")

        # 计算message应满足的长度范围：[minLen, maxLen]，确保radix^minLen >= 1,000,000
        # 数值型字符串长度应超过6比特，字符型（a-z、A-Z）应超过4比特，混合型应超过4比特
        self.minLen = math.ceil(math.log(FF1.DOMAIN_MIN) / math.log(radix))

        # 明文最大长度：FF1--2^32; FF3-1--radix: 2 * Floor(96/log2(radix))
        """FF3-1--radix:10-maxLen:56, radix:36-maxLen:36, radix:62-maxLen:32"""
        self.maxLen = 2 ** 32

        # 确保 2 <= minLen <= maxLen <= 2^32
        if(self.minLen < 2) or (self.maxLen < self.minLen):
            raise ValueError(f"minLen or maxLen invalid, adjust your radix")

    # 工厂方法：创建一个带有自定义字母表的FF1_AES对象
    @staticmethod
    def withCustomAlphabet(key, tweak, alphabet):
        c = FF1(key, tweak, len(alphabet))  # 创建一个 FF1_AES 实例
        c.alphabet = alphabet  # 设置自定义的字母表
        c.radix = len(alphabet)
        return c  # 返回创建的 FF1_AES 对象


    def encrypt(self, message):
        return self.encrypt_with_tweak(message)


    """
    Feistel structure

            u length |  v length
            A block  |  B block

                C <- modulo function

            B' <- C  |  A' <- B


    Steps:
    Let u = [n/2]
    Let v = n - u
    Let A = X[1..u]
    Let B = X[u+1,n]
    Let b = [[v * LOG(radix)] / 8]
    Let d = 4 * [b/4] + 4
    Let P = [1]^1 || [2]^1 || [1]^1 || [radix]^3 || [10]^1 || [u mod 256]^1 || [n]^4 || [t]^4
    Let T(L) = T[0..31] and T(R) = T[32..63]
    for i <- 0..9 do
        If is even, let m = u and W = T(R) Else let m = v and W = T(L)
        Let Q = T || [0]^(−t−b−1) mod 16 || [i]^1 || [NUMradix(B)]^b
        Let R = PRF(P || Q)
        Let S be the first d bytes of the following string of [d/16] blocks:
        R || CIPHk(R ＋ [1]^16) || CIPHk (R ＋ [2]^16) || … || CIPHk(R + [d/16–1]^16).
        Let Y = NUM(S)
        Let c = (NUM<radix>(A) + y) mod radix^m
        Let C = STR<radix>^m(c)
        Let A = B
        Let B = C
    end for
    Return A || B

    See spec and examples:

    https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-38Gr1-draft.pdf
    https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/FF1samples.pdf
    """

    def encrypt_with_tweak(self, message):
        """
        input: message--数值型字符串、tweak--字节字符串
        output: ciphertext--数值型字符串
        """
        if self.tweak is None:
            tweak = b''
        else:
            tweak = bytes.fromhex(self.tweak) # 将十六进制字符串转为字节序列

        n = len(message)
        if n < self.minLen or n > self.maxLen:
            raise ValueError(f"message length {n} is not within min {self.minLen} and"
                             f"max {self.maxLen} bounds")

        logger.debug(f"radix = {self.radix}")
        logger.debug(f"encrypt...")

        # 将明文分为左右两部分
        left, right, len_left, len_right = self.split_string(message)

        # 可加入对tweak的处理：长度、分割Tl和Tr

        # 计算编码后的左侧部分长度--b
        right_after_encoded_length = self.calculate_right_length(len_right, self.radix)

        # 计算d
        d = 4 * math.ceil(right_after_encoded_length / 4) + 4

        # 生成初始填充--P(字节字符串)
        padding = self.generate_initial_padding(self.radix, len(message), len(tweak) if tweak else 0, len_left)

        logger.debug(f"b={right_after_encoded_length}, d={d}, padding: {padding}")

        # Feistel网络
        for round in range(self.NUM_ROUNDS):
            logger.debug(f"round {round}")

            # 计算--y(数值型字符串)
            round_numeral = self.round_numeral(
                right,
                tweak,
                padding,
                right_after_encoded_length, # b
                d,
                round
            )

            # 计算m、c，如果需要对tweak处理，应该包含在m的处理中
            partial_length = len_left if round % 2 == 0 else len_right
            partial_numeral = (self.num(left, self.radix) + round_numeral) % (self.radix ** partial_length)

            # 计算C
            partial_block = self.str_m_radix(partial_length, self.radix, partial_numeral)

            # 更新 Feistel 网络的左右部分
            left = right
            right = partial_block

            logger.debug(f"left: {left}, right: {right}")

        # 返回加密后的结果（左右部分拼接）
        return ''.join(left + right)

    def decrypt(self, ciphertext): # 测试完删除默认参数值
        return self.decrypt_with_tweak(ciphertext)

    def decrypt_with_tweak(self, ciphertext):
        """
        input: ciphertext--数值型字符串、tweak--字节字符串
        output: message--数值型字符串
        """
        if self.tweak is None:
            tweak = b''
        else:
            tweak = bytes.fromhex(self.tweak) # 将十六进制字符串转为字节序列

        n = len(ciphertext)
        if n < self.minLen or n > self.maxLen:
            raise ValueError(f"ciphertext length {n} is not within min {self.minLen} and"
                             f"max {self.maxLen} bounds")


        """ 此处忽略对tweak的长度范围检查"""


        logger.debug(f"Decrypt...")

        # 将密文分为左右两部分
        left, right, len_left, len_right = self.split_string(ciphertext)

        # 可加入对tweak的处理：长度、分割Tl和Tr

        # 计算编码后的左侧部分长度--b
        right_after_encoded_length = self.calculate_right_length(len_right, self.radix)

        # 计算d
        d = 4 * math.ceil(right_after_encoded_length / 4) + 4

        # 生成初始填充--P(字节字符串)
        padding = self.generate_initial_padding(self.radix, len(ciphertext), len(tweak) if tweak else 0, len_left)

        logger.debug(f"b={right_after_encoded_length}, d={d}, padding: {padding}")

        # Feistel网络
        for round in range(self.NUM_ROUNDS - 1, -1, -1):
            logger.debug(f"round {round}")

            # 计算--y(数值型字符串)
            round_numeral = self.round_numeral(
                left,
                tweak,
                padding,
                right_after_encoded_length, # b
                d,
                round
            )

            # 计算m、c，如果需要对tweak处理，应该包含在m的处理中
            partial_length = len_left if round % 2 == 0 else len_right
            partial_numeral = (self.num(right, self.radix) - round_numeral) % (self.radix ** partial_length)

            # 计算C
            partial_block = self.str_m_radix(partial_length, self.radix, partial_numeral)

            # 更新 Feistel 网络的左右部分
            right = left
            left = partial_block

            logger.debug(f"left: {left}, right: {right}")

        # 返回加密后的结果（左右部分拼接）
        return ''.join(left + right)


    def split_string(self, message):
        """ 将数字字符串分为左右两部分：n为偶数，len(A)=len(B)；n为奇数，len(A)=len(B)-1 """
        n = len(message)
        u = n // 2 # 向下取整
        v = n - u

        A = message[:u]
        B = message[u:]
        logger.debug(f"A: {A}, B: {B}, len_A={u}, len_B={v}")
        return A, B, u, v

    def calculate_right_length(self, len_right, radix):
        # 计算编码后左侧部分的长度--b
        return math.ceil(len_right * math.ceil(math.log2(radix)) / 8.0)

    def generate_initial_padding(self, radix, len_message, len_tweak, len_left):
        """ P--字节字符串 """
        padding = bytearray([0x01, 0x02, 0x01])

        padding.extend(self.number_to_array_of_bytes(radix, 3))

        padding.extend([0x0A])

        padding.extend([len_left % 256])

        padding.extend(self.number_to_array_of_bytes(len_message, 4))

        padding.extend(self.number_to_array_of_bytes(len_tweak, 4))

        return bytes(padding)

    def number_to_array_of_bytes(self, value, length):
        """ 将 数字 转换为指定字节长度的字节数组 """
        max_value = 256 ** length
        if value >= max_value:
            raise ValueError(f"Value {value} exceeds the maximum value for {length} bytes.")

        return value.to_bytes(length, byteorder='big') # byteorder='big' 表示使用大端字节序（即高位字节在前）

    def round_numeral(self, target_block_numeral, tweak, padding, right_after_encoded_length, d, round):
        """ 计算--y """
        # 计算--Q（字节字符串）
        q = self.generate_q(tweak, target_block_numeral, right_after_encoded_length, round)
        logger.debug(f"Q={q}")

        # 通过轮函数计算当前轮的加密块（bytes）--计算R、S
        round_block = self.round_function(padding, q, d)

        # 返回长度为d的round_block并转换为整数
        s = round_block[:d]
        y = bytes_to_long(s) # 字节序列转换为整数
        logger.debug(f"S={s}, y={y}")

        return y

    def generate_q(self, tweak, target_block_numeral, right_after_encoded_length, round):
        """ 计算--Q(字节字符串) """
        # 计算 mod(- len(tweak) - length_of_left_after_encoded - 1, 16)
        len_tweak = len(tweak)
        zero_padding_length = self.mod(-len_tweak - right_after_encoded_length - 1, 16)

        # 构建 Q
        q = tweak + self.number_to_array_of_bytes(0, zero_padding_length) \
            + self.number_to_array_of_bytes(round, 1) \
            + self.number_to_array_of_bytes(self.num(target_block_numeral, self.radix), right_after_encoded_length)

        return q

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

    def str_m_radix(self, m, radix, x):
        """ 将数字 x 转换为长 m 字节、以 radix 为基的字符串 """
        if not (0 <= x <= radix ** m): # 范围检查
            raise ValueError(f"x={x} is out of range [0, {radix ** m}].")

        result = [0] * m

        for i in range(m):
            result[m - 1 - i] = self.alphabet[x % radix]
            x = x // radix

        return ''.join(result)

    def mod(self, a, b):
        return (a % b + b) % b

    def xor(self, a, b):
        """ 按位异或 """
        return bytes(a ^ b for a, b in zip(a, b))

    def num(self, value, radix):
        """ 把 value 转换为以 radix 为基数的整数 """
        char_to_value = {}
        if self.alphabet:
            char_to_value = {char : i for i, char in enumerate(self.alphabet)}
        # if radix <= 10:
        #     return int(value, radix)
        #
        # char_to_value = {}
        #
        # for i in range(10):
        #     char_to_value[str(i)] = i
        # for i, char in enumerate(string.ascii_lowercase, start=10):
        #     char_to_value[char] = i
        # for i, char in enumerate(string.ascii_uppercase, start=36):
        #     char_to_value[char] = i

        number = 0
        for char in value:
            i = char_to_value[char]
            number = number * radix + i

        return number


"""
if __name__ == '__main__':
    cipher = FF1.withCustomAlphabet(b'0123456789abcdef', None, string.digits + string.ascii_lowercase + string.ascii_uppercase)
    # message = "90313454390"
    # message = "sxdfrgfdgfb"
    message = "hifsaeu89u42"
    ciphertext = cipher.encrypt(message)
    plaintext = cipher.decrypt(ciphertext)

    logger.debug(f"message: {message}, ciphertext: {ciphertext}, plaintext: {plaintext}")
    assert message == plaintext, f"ERROR! {message} != {plaintext}"
"""