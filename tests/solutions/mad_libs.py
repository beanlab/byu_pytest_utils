def mad_libs():
    print("Welcome to Mad Libs!")
    print("Please enter the following words:")
    noun1 = input("Noun: ")
    adjective1 = input("Adjective: ")
    adjective2 = input("Adjective: ")
    noun2 = input("Noun: ")
    number = input("Number: ")
    adjective3 = input("Adjective: ")
    verb1 = input("Past-Tense Verb: ")
    game = input("Game: ")
    verb2 = input("Verb: ")

    print(f"Once upon a time a student at found themselves in a {noun1} class.")
    print(f"The teacher was so {adjective1} that the student started to daydream about a {noun2}.")
    print(f"Then the student woke up and realized that they were still in class.")
    print(f"The teacher was so {adjective2} that they gave the student a {number} on the assignment.")
    print(f"The student was so {adjective3} that he {verb1} the class and went home to play {game}.")
    print(f"The moral of the story is that you should never {verb2} in class.")


if __name__ == '__main__':
    mad_libs()