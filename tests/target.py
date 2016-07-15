import sys

import afl

def main():
    s = sys.stdin.read()
    if len(s) < 1:
        print('Hum?')
        sys.exit(1)
    s.encode('ASCII')
    if s[0] == '0':
        print('Looks like a zero to me!')
    else:
        print('A non-zero value? How quaint!')

if __name__ == '__main__':
    afl.init()
    main()

# vim:ts=4 sts=4 sw=4 et
