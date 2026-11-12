import csv


def load_csv(filename):
    with open(filename, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))