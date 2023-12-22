import sys

if __name__ == '__main__':
    print("My args:", sys.argv)
    list = [1, 2, 3]
    for item in list:
        print(item)
        list.append(item + 3)
