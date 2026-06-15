# 自动生成一个唯一的id函数
import random
import string

def generate_id(prefix: str, k=29) -> str:
    """
    随机生成一个29长度的字符串，这个字符串有大，小写字母和数字组成
    prefix是ID的前缀，
    k 是 id的长度
    """
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
    return f"{prefix}{suffix}"

if __name__ == '__main__':
    print(generate_id('SKI:'))
