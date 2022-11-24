import random
from hashlib import md5
from Crypto.Cipher import AES
from os import urandom


def derive_key_and_iv(password, salt, key_length, iv_length):  # derive key and IV from password and salt.
    d = d_i = b''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + str.encode(password) + salt).digest()  # obtain the md5 hash value
        d += d_i
    return d[:key_length], d[key_length:key_length + iv_length]


def encrypt(in_file, out_file, key_length=32):
    bs = AES.block_size  # 16 bytes
    salt = urandom(bs)  # return a string of random bytes
    password = str(random.randint(1000, 10000))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    out_file.write(salt)
    finished = False

    while not finished:
        chunk = in_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:  # final block/chunk is padded before encryption
            padding_length = (bs - len(chunk) % bs) or bs
            chunk += str.encode(padding_length * chr(padding_length))
            finished = True
        out_file.write(cipher.encrypt(chunk))
    return password


def decrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = in_file.read(bs)
    key, iv = derive_key_and_iv(str(password), salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False
    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
        print(chunk)
        if len(next_chunk) == 0:
            padding_length = chunk[-1]
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(bytes(x for x in chunk))


# infile = 'hi.docx'
# outfile = 'hi.docx.enc'
# with open(infile, 'rb') as in_file1, open(outfile, 'wb') as out_file1:
#     encrypt(in_file1, out_file1, Password)
#
# Password = '12345'
# infile = 'hi.docx.enc'
# outfile = 'hi_final.docx'
# with open(infile, 'rb') as in_file1, open(outfile, 'wb') as out_file1:
#     decrypt(in_file1, out_file1, Password)




# def encrypt(filename, key_length=32):
#     filename = open(filename, 'rb')
#     bs = AES.block_size  # 16 bytes
#     salt = urandom(bs)  # return a string of random bytes
#     password = str(random.randint(1000, 10000))
#     key, iv = derive_key_and_iv(password, salt, key_length, bs)
#     cipher = AES.new(key, AES.MODE_CBC, iv)
#     out_file1 = open('encrypted.enc', 'wb')
#     out_file1.write(salt)
#     finished = False
#
#     while not finished:
#
#         chunk = filename.read(1024 * bs)
#         if len(chunk) == 0 or len(chunk) % bs != 0:  # final block/chunk is padded before encryption
#             padding_length = (bs - len(chunk) % bs) or bs
#             chunk += str.encode(padding_length * chr(padding_length))
#             finished = True
#         out_file1.write(cipher.encrypt(chunk))
#     return password





# def decrypt(in_file, password, key_length=32):
#     in_file = open(in_file, 'rb')
#     bs = AES.block_size
#     salt = in_file.read(bs)
#
#     key, iv = derive_key_and_iv(str(password), salt, key_length, bs)
#     cipher = AES.new(key, AES.MODE_CBC, iv)
#     next_chunk = ''
#     finished = False
#     while not finished:
#         chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
#         print(chunk)
#         if len(next_chunk) == 0:
#             padding_length = chunk[-1]
#             chunk = chunk[:-padding_length]
#             finished = True
#         in_file.close()
#         with open(in_file, 'wb') as out_file1:
#             out_file1.write(bytes(x for x in chunk))





# infile = 'java2.txt'
# outfile = 'java.txt.enc'
# with open(infile, 'rb') as in_file1, open(outfile, 'wb') as out_file1:
#     hello = encrypt(in_file1, out_file1)
#     print(hello)

# Password = 5406
# infile = 'java.txt.enc'
# outfile = 'java_final.txt'
# with open(infile, 'rb') as in_file1, open(outfile, 'wb') as out_file1:
#     decrypt(in_file1, out_file1, Password)

# file_name = 'java.txt'

# with open(file_name, 'rb') as in_file1:
# hello = encrypt(file_name)
# print(hello)



# Password = 9960
# infile = 'encrypted.txt'
#
# with open(infile, 'rb') as in_file1:
#     decrypt(in_file1, infile, Password)

# filename = 'encrypted.enc'
# password = 4489
# decrypt(filename, password)
