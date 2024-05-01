def main():
    names = []
    while True:
        response = input('What is your name? ')
        if not response:
            break
        names.append(response)
    print('The names are:')
    for name in names:
        print(name)


if __name__ == '__main__':
    main()