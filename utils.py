import re
from typing import List
from datetime import date, timedelta
from dateutil.parser import parse


def transform_datetime_to_date(datetime_str: str, time_delta: int = 0):
    datetime_obj = parse(datetime_str) + timedelta(time_delta)
    date_str = datetime_obj.date().isoformat()
    return date_str


def transform_range_date_to_date(date_range_str: str):
    # current_year = date.today().year
    date_range_str_cleaned = remove_non_words(date_range_str).replace(" ", "")
    # print(date_range_str_cleaned)

    date_parts = date_range_str_cleaned.split("~")

    # Check if the date range has '~' separator
    if len(date_parts) == 1:
        # transformed_date = f"{current_year}-{date_parts[0].replace('.', '-')}"
        transformed_date = f"{date_parts[0].replace('.', '-')}"
    else:
        start_date = date_parts[0]
        end_date = date_parts[1]

        # Check if the end date is in the following year
        if end_date < start_date:
            current_year += 1

        # transformed_date = f"{current_year}-{end_date.replace('.', '-')}"
        transformed_date = f"{end_date.replace('.', '-')}"

    return transformed_date


def remove_non_words(string: str):
    # patterns = [" ", "\n"]
    pattern = re.compile(r"\s+|\n")
    # pattern_regex = "|".join(map(re.escape, patterns))
    string = re.sub(pattern, "", string)

    return string


def find_non_matched_items(new_items: List, existing_items: List) -> List:
    non_matched_items = []

    for item in new_items:
        if item not in existing_items:
            non_matched_items.append(item)

    return non_matched_items
