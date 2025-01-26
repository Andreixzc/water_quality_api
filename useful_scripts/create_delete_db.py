import subprocess

def execute_command(command):
    """
    Executes a shell command and handles errors.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr.strip()}")

def manage_database(db_name, action):
    """
    Creates or drops a PostgreSQL database.

    :param db_name: Name of the database to create/drop.
    :param action: Action to perform: 'create' or 'drop'.
    """
    if action == "create":
        command = f"sudo -i -u postgres createdb {db_name}"
        print(f"Creating database '{db_name}'...")
    elif action == "drop":
        command = f"sudo -i -u postgres dropdb {db_name}"
        print(f"Dropping database '{db_name}'...")
    else:
        print("Invalid action. Use 'create' or 'drop'.")
        return

    execute_command(command)

if __name__ == "__main__":
    db_name = "water-quality-db"

    # Drop the database if it exists
    manage_database(db_name, "drop")

    # Create the database
    manage_database(db_name, "create")
