import html
import re
from urllib.request import Request, urlopen

from tools import ToolBox

toolbox = ToolBox()


@toolbox.tool
def fetch_url(url: str) -> str:
    """Fetch a web page and return its text, with links shown as text (url)."""
    request = Request(url, headers={"User-Agent": "CS301-tool-calling-demo/1.0"})  # default Python agent gets 403s
    page = urlopen(request).read().decode()
    page = re.sub(r"(?is)<(script|style).*?</\1>", "", page)  # remove code and CSS
    page = re.sub(r'(?is)<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2 (\1)", page)  # keep links as "text (url)"
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))  # remove the remaining tags
    return " ".join(text.split())  # collapse whitespace
