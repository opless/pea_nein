import os

next_ch = b'R'
while True:
    x = os.read(1, 1)
    if x == next_ch:
        if x == b'R':
            next_ch = b'E'
        elif x == b'E':
            next_ch = b'A'
        elif x == b'A':
            next_ch = b'D'
        elif x == b'D':
            next_ch = b'Y'
        elif x == b'Y':
            break
    else:
        x = b'R'
