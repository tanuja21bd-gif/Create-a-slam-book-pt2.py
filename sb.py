"""Slam Book - a small command-line app to keep notes about your friends.

Entries are saved to slambook.json so they are still there next time you run it.
"""

import json
import os
import re
from datetime import datetime

DATA_FILE = "slambook.json"
CATEGORIES = ["Family", "Friends", "Work", "Others"]
LINE = "=" * 60


# ---------- storage ----------

def load_book():
    """Load entries from disk. Returns an empty list if nothing is saved yet."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print("Could not read the saved slam book. Starting with an empty one.")
        return []


def save_book(book):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(book, f, indent=2, ensure_ascii=False)


# ---------- input helpers ----------

def ask(prompt, required=False, default=None):
    """Ask for text. Re-asks if a required field is left blank."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return None
        print("  This field is required.")


def ask_phone(prompt, default=None):
    """Phone numbers are stored as text so leading zeros and '+' are kept."""
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        cleaned = re.sub(r"[\s\-()]", "", value)
        if re.fullmatch(r"\+?\d{6,15}", cleaned):
            return cleaned
        print("  Please enter a valid number (6-15 digits, optional leading +).")


def ask_dob(prompt, default=None):
    """Accepts dd/mm/yyyy. Blank is allowed (keeps default / None)."""
    while True:
        value = input(prompt).strip()
        if not value:
            return default
        try:
            datetime.strptime(value, "%d/%m/%Y")
            return value
        except ValueError:
            print("  Please use dd/mm/yyyy, e.g. 25/12/2005.")


def ask_category(prompt, default=None):
    while True:
        value = input(prompt).strip().title()
        if not value:
            return default
        if value in CATEGORIES:
            return value
        print(f"  Choose one of: {', '.join(CATEGORIES)}")


def ask_int(prompt, low, high):
    while True:
        try:
            n = int(input(prompt))
            if low <= n <= high:
                return n
        except ValueError:
            pass
        print(f"  Enter a number between {low} and {high}.")


def confirm(prompt):
    return input(prompt + " (y/n): ").strip().lower() in ("y", "yes")


# ---------- display ----------

def age_from_dob(dob):
    try:
        born = datetime.strptime(dob, "%d/%m/%Y")
    except (TypeError, ValueError):
        return None
    today = datetime.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def show_entry(entry, index=None):
    head = f"#{index} " if index is not None else ""
    print(f"\n{head}{entry['name']}  [{entry.get('category') or 'Uncategorised'}]")
    print(f"  Phone : {entry['phone']}")
    print(f"  About : {entry.get('about') or '-'}")
    dob = entry.get("dob")
    age = age_from_dob(dob)
    print(f"  DOB   : {dob or '-'}" + (f"  (age {age})" if age is not None else ""))


def show_list(entries):
    if not entries:
        print("\nNothing to show.")
        return
    for i, e in enumerate(entries, 1):
        show_entry(e, i)
    print(f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")


# ---------- actions ----------

def add_entry(book):
    print("\n--- Add a friend (* = required) ---")
    name = ask("Name*: ", required=True)
    if any(e["name"].lower() == name.lower() for e in book):
        if not confirm(f"'{name}' already exists. Add anyway?"):
            return
    entry = {
        "name": name,
        "phone": ask_phone("Phone number*: "),
        "about": ask("Something about your friend: "),
        "dob": ask_dob("Date of birth (dd/mm/yyyy, optional): "),
        "category": ask_category(f"Category ({'/'.join(CATEGORIES)}, optional): "),
    }
    book.append(entry)
    save_book(book)
    print(f"\nSaved {name}.")


def view_all(book):
    show_list(sorted(book, key=lambda e: e["name"].lower()))


def search(book):
    term = input("\nSearch by name, phone or note: ").strip().lower()
    if not term:
        return
    hits = [
        e for e in book
        if term in e["name"].lower()
        or term in e["phone"]
        or term in (e.get("about") or "").lower()
    ]
    show_list(hits)


def filter_category(book):
    print("\nCategories: " + ", ".join(f"{i}. {c}" for i, c in enumerate(CATEGORIES, 1)))
    choice = ask_int("Pick a category: ", 1, len(CATEGORIES))
    show_list([e for e in book if e.get("category") == CATEGORIES[choice - 1]])


def pick_entry(book):
    """Let the user choose an entry by searching a name."""
    term = input("\nName of the friend: ").strip().lower()
    matches = [e for e in book if term and term in e["name"].lower()]
    if not matches:
        print("No match found.")
        return None
    if len(matches) == 1:
        return matches[0]
    for i, e in enumerate(matches, 1):
        print(f"  {i}. {e['name']} ({e['phone']})")
    return matches[ask_int("Which one? ", 1, len(matches)) - 1]


def edit_entry(book):
    entry = pick_entry(book)
    if not entry:
        return
    print("\nPress Enter to keep the current value.")
    entry["name"] = ask(f"Name [{entry['name']}]: ", default=entry["name"])
    entry["phone"] = ask_phone(f"Phone [{entry['phone']}]: ", default=entry["phone"])
    entry["about"] = ask(f"About [{entry.get('about') or '-'}]: ", default=entry.get("about"))
    entry["dob"] = ask_dob(f"DOB [{entry.get('dob') or '-'}]: ", default=entry.get("dob"))
    entry["category"] = ask_category(
        f"Category [{entry.get('category') or '-'}]: ", default=entry.get("category")
    )
    save_book(book)
    print("\nUpdated.")


def delete_entry(book):
    entry = pick_entry(book)
    if entry and confirm(f"Delete {entry['name']}?"):
        book.remove(entry)
        save_book(book)
        print("Deleted.")


def upcoming_birthdays(book):
    today = datetime.today().date()
    upcoming = []
    for e in book:
        try:
            dob = datetime.strptime(e.get("dob") or "", "%d/%m/%Y").date()
        except ValueError:
            continue
        try:
            nxt = dob.replace(year=today.year)
        except ValueError:  # 29 Feb in a non-leap year
            nxt = dob.replace(year=today.year, day=28)
        if nxt < today:
            nxt = nxt.replace(year=today.year + 1)
        upcoming.append(((nxt - today).days, e["name"], nxt))
    if not upcoming:
        print("\nNo birthdays saved yet.")
        return
    print("\nNext birthdays:")
    for days, name, when in sorted(upcoming)[:5]:
        label = "today!" if days == 0 else f"in {days} day(s)"
        print(f"  {name:<20} {when.strftime('%d %b')}  ({label})")


# ---------- menu ----------

MENU = [
    ("Add a friend", add_entry),
    ("View all", view_all),
    ("Search", search),
    ("Filter by category", filter_category),
    ("Edit an entry", edit_entry),
    ("Delete an entry", delete_entry),
    ("Upcoming birthdays", upcoming_birthdays),
]


def menu():
    print("\n" + LINE)
    print("SLAM BOOK".center(60))
    print(LINE)
    for i, (label, _) in enumerate(MENU, 1):
        print(f"  {i}. {label}")
    print("  0. Exit")
    print(LINE)


def main():
    book = load_book()
    print(f"Loaded {len(book)} entr{'y' if len(book) == 1 else 'ies'} from {DATA_FILE}.")
    while True:
        menu()
        choice = ask_int("Choose an option: ", 0, len(MENU))
        if choice == 0:
            print("Goodbye!")
            break
        MENU[choice - 1][1](book)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")