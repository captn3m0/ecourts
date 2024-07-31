from collections import OrderedDict
from datetime import datetime
from typing import List, Dict, Optional
import re


def parse_js_call(js_call, signature):
    """
    Parses a JavaScript function call and returns a dictionary of typed arguments.

    Args:
      js_call: The JavaScript function call as a string.
      signature: An OrderedDict mapping argument names to their types.

    Returns:
      A dictionary of typed arguments.
    """

    # Extract arguments from the JavaScript function call
    args_str = re.search(r"\((.*)\)", js_call).group(1)
    args = [arg.strip() for arg in args_str.split(",")]

    # Convert arguments to typed values based on the signature
    typed_args = {}
    while signature:
        key, type_ = signature.popitem(last=False)
        arg = args.pop(0)
        arg = arg.strip("'\"")  # Remove leading and trailing quotes
        try:
            typed_args[key] = type_(arg)
        except ValueError:
            raise ValueError(f"Invalid argument type for {arg}: expected {type_}")

    return typed_args


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    date_formats = ["%d-%m-%Y", "%dth %B %Y", "%dst %B %Y", "%dnd %B %Y", "%Y%m%d"]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None


def _remove_all_attrs_except_saving(soup):
    for tag in soup.find_all(True):
        for attr in dict(tag.attrs):
            if attr not in ["href", "onclick", "id", "class"]:
                del tag.attrs[attr]
    return soup


def clean_html(soup) -> str:
    soup = _remove_all_attrs_except_saving(soup)
    soup = soup.select_one("body")
    return str(soup)