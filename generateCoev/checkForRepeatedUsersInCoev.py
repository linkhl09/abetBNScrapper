import csv
from collections import Counter


def find_repeated_usernames(csv_path: str, username_column: str = "Username"):
    usernames = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or username_column not in reader.fieldnames:
            raise ValueError(f"Column '{username_column}' not found in {csv_path}")

        for row in reader:
            username = (row.get(username_column) or "").strip()
            if username:
                usernames.append(username)

    counts = Counter(usernames)
    return {u: c for u, c in counts.items() if c > 1}


if __name__ == "__main__":
    file_path = "uploadEAGrades.csv"
    repeated = find_repeated_usernames(file_path)

    if repeated:
        print("Repeated usernames found:")
        for username, count in sorted(repeated.items()):
            print(f"- {username}: {count} times")
    else:
        print("No repeated usernames found.")
