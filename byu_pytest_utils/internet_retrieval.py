import urllib
import urllib.error
from urllib.request import urlopen, Request
import shutil
from shutil import unpack_archive, rmtree
import os
import glob


def get_test_files_from_website(assignment_name: str):
    """Expects
    Deletes the test_files directory if present
    Requests the zip file from the given url and unpacks it
    Restructures the directory to only leave the .txt files"""
    zip_url = f'https://winter2023.byucs110.org/files/{assignment_name}.zip'
    request_site = Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
    # Try to get the files, catch if no internet connection
    try:
        with urlopen(request_site) as zip_response:
            # Removes the old test_file directory and everything inside, ignores if it is not found
            try:
                rmtree(test_files)
            except FileNotFoundError:
                pass
            # Create test_files again, so we can unzip to the folder
            os.mkdir(test_files)
            # Create a temporary file to write to
            with open(test_files / "temp.zip", 'wb') as tempfile:
                # Get the zip file from the website
                tempfile.write(zip_response.read())
                tempfile.seek(0)
            # Close the temporary file for writing

        # Unzips the zip file to the test_files location
        unpack_archive(tempfile.name, test_files, format='zip')
        os.remove(tempfile.name)
        # Remove all python files from the folder
        python_file_regex = str(test_files / "*.py")
        for f in glob.glob(python_file_regex):
            os.remove(str(f))
        # Move all text files up a level (Get them out of the inner test_files folder)
        text_file_regex = str(test_files / "test_files" / "*.txt")
        for f in glob.glob(text_file_regex):
            shutil.copy(f, test_files)
        # Remove the inner test_files folder
        try:
            rmtree(test_files / "test_files")
        except FileNotFoundError:
            print()
            print("No test_files folder was found in the zip file downloaded from the website")

    except urllib.error.URLError:
        pass
