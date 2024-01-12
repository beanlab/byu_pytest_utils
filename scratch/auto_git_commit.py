import argparse
import subprocess
import time


def commit_changes(interval_seconds, commit_message):
    try:
        while True:
            # Check for changes; proceed only if there are changes
            status_result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if status_result.stdout.strip():  # There are changes to commit
                # Add all changes to staging
                subprocess.run(['git', 'add', '.'], check=True)

                # Commit with a predefined message
                subprocess.run(
                    ['git', 'commit', '-m', commit_message],
                    check=True
                )
                print(f"Committed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"No changes to commit at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Wait for the specified interval
            time.sleep(interval_seconds)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while trying to perform git operations: {e}")
        # In case of error, you may want to sleep for a bit before the next iteration
        time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nAuto git commit script terminated by user.")
    except Exception as ex:
        print(f"An error occurred: {ex}")


def main():
    parser = argparse.ArgumentParser(
        description="Automatically commit changes to a Git repository at regular intervals.")
    parser.add_argument('interval', type=int, help='Interval in seconds between commits.')
    parser.add_argument('-m', '--message', type=str, default='Auto commit',
                        help='Commit message. Default is "Auto commit".')

    args = parser.parse_args()

    commit_changes(args.interval, args.message)


if __name__ == "__main__":
    main()
