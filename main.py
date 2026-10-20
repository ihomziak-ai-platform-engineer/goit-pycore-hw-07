from collections import UserDict
from datetime import date, datetime, timedelta
from functools import wraps
import re


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    def __init__(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Ім'я контакту не може бути порожнім.")
        super().__init__(value)


class Phone(Field):
    def __init__(self, value):
        if (
                not isinstance(value, str)
                or len(value) != 10
                or not value.isascii()
                or not value.isdigit()
        ):
            raise ValueError("Телефон повинен містити рівно 10 цифр.")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value):
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        try:
            birthday = datetime.strptime(value, "%d.%m.%Y")
        except ValueError as exc:
            raise ValueError("Invalid date format. Use DD.MM.YYYY") from exc
        super().__init__(birthday)

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")


class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        for item in self.phones:
            if item.value == phone:
                self.phones.remove(item)
                return

    def edit_phone(self, old_phone, new_phone):
        for index, phone in enumerate(self.phones):
            if phone.value == old_phone:
                self.phones[index] = Phone(new_phone)
                return
        raise ValueError(f"Телефон {old_phone} не знайдено.")

    def find_phone(self, phone):
        for item in self.phones:
            if item.value == phone:
                return item
        return None

    def add_birthday(self, birthday):
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(str(phone) for phone in self.phones) or "немає"
        birthday = f", день народження: {self.birthday}" if self.birthday else ""
        return f"Контакт: {self.name}, телефони: {phones}{birthday}"


class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        self.data.pop(name, None)

    def get_upcoming_birthdays(self):
        today = date.today()
        result = []
        for record in self.data.values():
            if record.birthday is None:
                continue

            born = record.birthday.value.date()

            def anniversary(year):
                try:
                    return born.replace(year=year)
                except ValueError:
                    # 29 лютого в невисокосний рік відзначаємо 28 лютого.
                    return date(year, 2, 28)

            upcoming = anniversary(today.year)
            if upcoming < today:
                upcoming = anniversary(today.year + 1)

            if not 0 <= (upcoming - today).days <= 7:
                continue

            greeting = upcoming
            if greeting.weekday() == 5:  # субота -> понеділок
                greeting += timedelta(days=2)
            elif greeting.weekday() == 6:  # неділя -> понеділок
                greeting += timedelta(days=1)

            result.append({
                "name": record.name.value,
                "congratulation_date": greeting.strftime("%Y.%m.%d"),
            })

        return sorted(result, key=lambda item: (item["congratulation_date"], item["name"]))


def input_error(func):
    @wraps(func)
    def wrapper(args, book):
        try:
            return func(args, book)
        except (ValueError, LookupError) as exc:
            return f"Помилка: {exc}"

    return wrapper


def require_args(args, count, usage):
    if len(args) != count:
        raise ValueError(f"Використання: {usage}")
    return args


def require_record(book, name):
    record = book.find(name)
    if record is None:
        raise ValueError(f"Контакт '{name}' не знайдено.")
    return record


@input_error
def add_contact(args, book):
    name, phone = require_args(args, 2, "add [ім'я] [телефон]")
    record = book.find(name)
    if record is None:
        record = Record(name)
        record.add_phone(phone)
        book.add_record(record)
        return "Контакт додано."
    record.add_phone(phone)
    return "Номер додано до контакту."


@input_error
def change_contact(args, book):
    name, old_phone, new_phone = require_args(
        args, 3, "change [ім'я] [старий телефон] [новий телефон]"
    )
    record = require_record(book, name)
    record.edit_phone(old_phone, new_phone)
    return "Номер телефону змінено."


@input_error
def show_phone(args, book):
    (name,) = require_args(args, 1, "phone [ім'я]")
    record = require_record(book, name)
    return f"{record.name}: " + ("; ".join(str(p) for p in record.phones) or "немає телефонів")


@input_error
def show_all(args, book):
    require_args(args, 0, "all")
    return "\n".join(str(record) for record in book.data.values()) or "Адресна книга порожня."


@input_error
def add_birthday(args, book):
    name, birthday = require_args(args, 2, "add-birthday [ім'я] [DD.MM.YYYY]")
    record = require_record(book, name)
    record.add_birthday(birthday)
    return "День народження збережено."


@input_error
def show_birthday(args, book):
    (name,) = require_args(args, 1, "show-birthday [ім'я]")
    record = require_record(book, name)
    if record.birthday is None:
        return f"У контакту '{name}' день народження не вказано."
    return f"{name}: {record.birthday}"


@input_error
def birthdays(args, book):
    require_args(args, 0, "birthdays")
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "Немає днів народження протягом найближчих 7 днів."
    return "\n".join(
        f"{item['name']}: {item['congratulation_date']}"
        for item in upcoming
    )


def parse_input(user_input):
    parts = user_input.strip().split()
    return (parts[0].lower(), parts[1:]) if parts else ("", [])


def main():
    book = AddressBook()
    print("Ласкаво просимо до бота-помічника!")
    handlers = {
        "add": add_contact,
        "change": change_contact,
        "phone": show_phone,
        "all": show_all,
        "add-birthday": add_birthday,
        "show-birthday": show_birthday,
        "birthdays": birthdays,
    }

    while True:
        try:
            command, args = parse_input(input("Введіть команду: "))
        except (EOFError, KeyboardInterrupt):
            print("\nДо побачення!")
            break

        if not command:
            continue
        if command in ("exit", "close"):
            print("До побачення!")
            break
        if command == "hello":
            print("Чим можу допомогти?")
        elif command in handlers:
            print(handlers[command](args, book))
        else:
            print("Невідома команда.")


if __name__ == "__main__":
    main()
