import re
import traceback
from typing import List
from datetime import timedelta
from dateutil.parser import parse


def transform_datetime_to_date(datetime_str: str, time_delta: int = 0) -> str:
    """날짜/시간 문자열을 날짜 형식으로 변환합니다.

    Args:
        datetime_str: 변환할 날짜/시간 문자열
        time_delta: 날짜 조정값 (일 단위)

    Returns:
        ISO 형식의 날짜 문자열 (YYYY-MM-DD)
    """
    datetime_obj = parse(datetime_str) + timedelta(time_delta)
    date_str = datetime_obj.date().isoformat()
    return date_str


def transform_range_date_to_date(date_range_str: str):
    """날짜 범위 문자열을 단일 날짜로 변환합니다.

    Args:
        date_range_str: 변환할 날짜 범위 문자열 (예: "2025.03.01 ~ 2025.03.31")

    Returns:
        ISO 형식의 날짜 문자열 (YYYY-MM-DD)
    """
    date_range_str_cleaned = (
        remove_non_words(date_range_str).replace(" ", "").replace("  ", "")
    )
    # print(date_range_str_cleaned)

    date_parts = date_range_str_cleaned.split("~")

    if len(date_parts) == 1:
        transformed_date = f"{date_parts[0].replace('.', '-')}"
    else:
        start_date = date_parts[0]
        end_date = date_parts[1]

        if start_date > end_date:
            print(traceback.format_exc())
            raise ValueError("시작 날짜가 종료 날짜보다 늦습니다.")

        transformed_date = f"{end_date.replace('.', '-')}"

    return transformed_date


def remove_non_words(string: str) -> str:
    """문자열에서 공백과 줄바꿈을 제거합니다.

    Args:
        string: 처리할 문자열

    Returns:
        공백과 줄바꿈이 제거된 문자열
    """
    # patterns = [" ", "\n"]
    pattern = re.compile(r"\s+|\n")
    # pattern_regex = "|".join(map(re.escape, patterns))
    string = re.sub(pattern, "", string)

    return string


def find_non_matched_items(new_items: List, existing_items: List) -> List:
    """두 목록을 비교하여 일치하지 않는 항목을 찾습니다.

    Args:
        new_items: 새로운 항목 목록
        existing_items: 기존 항목 목록

    Returns:
        일치하지 않는 항목 목록
    """
    non_matched_items = []

    for item in new_items:
        if item not in existing_items:
            non_matched_items.append(item)

    return non_matched_items


# if __name__ == "__main__":
#     range_date = "2025.03.01 ~ 2025.03.31"
#     print(transform_range_date_to_date(range_date))
