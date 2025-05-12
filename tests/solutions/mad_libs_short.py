def mad_libs_short():
    print("Welcome to Mad Libs!")
    print("Please enter the following words:")
    character1 = input("Noun: ")
    adjective = input("Adjective: ")
    noun2 = input("Noun: ")
    character2 = input("Character: ")
    pet = input("Animal (Plural): ")

    print(f"{character1} sat on a {noun2}.")
    print(f"{character1} had a {adjective} fall.")
    print(f"All {character2}'s {pet} and all the {character2}'s men couldn't put {character1} together again.")


if __name__ == '__main__':
    mad_libs_short()