from rich import print
from rich.table import Table
import random

COLORS = ["red", "green", "blue", "yellow", "magenta", "cyan", "white", "bright_red", "bright_green", "bright_blue", "bright_yellow", "bright_magenta", "bright_cyan"]

def print_table(rows, title=None, headers=None):
    if not rows:
        return
    table = Table(title=title, show_lines=True)
    for header in headers:  
        # 为每一列随机选择一个颜色
        color = random.choice(COLORS)
        table.add_column(header, justify="center", style=f"bold {color}", no_wrap=True)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    print(table)

def print_records(records, title=None):
    if not records:
        return
    headers = type(records[0])._fields
    print_table(records, title=title, headers=headers)
