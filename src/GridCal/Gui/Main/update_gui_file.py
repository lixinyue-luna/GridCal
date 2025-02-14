"""
Script to update correctly the main GUI (.py) file from the Qt design (.ui) file
"""
from subprocess import call

if __name__ == '__main__':
    # pyrcc5 icons.qrc -o icons_rc.py
    # pyuic5 -x MainWindow.ui -o MainWindow.py

    file_names = ['MainWindow.py', 'ConsoleLog.py']
    file_names_ui = ['MainWindow.ui', 'ConsoleLog.ui']

    for filename, filename_ui in zip(file_names, file_names_ui):

        # update icon/images resources
        call(['pyside2-rcc', 'icons.qrc', '-o', 'icons_rc.py'])

        # update ui handler file
        call(['pyside2-uic', '-x', filename_ui, '-o', filename])

        # replace annoying text import
        # Read in the file
        with open(filename, 'r') as file:
            file_data = file.read()

        # Replace the target string
        file_data = file_data.replace('import icons_rc', 'from .icons_rc import *')

        # Write the file out again
        with open(filename, 'w') as file:
            file.write(file_data)
