"""Exact calculations, unit conversions and date arithmetic.

LLMs are bad at arithmetic, so the math agent always computes with tools.
"""
from __future__ import annotations

import ast
import datetime as dt
import math
import operator
import re
import statistics

from ..agent import Agent
from ..tools import tool

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {name: getattr(math, name) for name in
          ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "log", "log10", "log2",
           "exp", "floor", "ceil", "factorial", "radians", "degrees", "hypot", "gcd", "comb", "perm")}
_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum,
               "mean": statistics.mean, "median": statistics.median, "stdev": statistics.stdev})
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def safe_eval(expr: str) -> float | int:
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    expr = re.sub(r"(?<=\d),(?=\d{3}\b)", "", expr)  # 1,250,000 -> 1250000

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10000:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name) and node.id in _CONSTS:
            return _CONSTS[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [ev(e) for e in node.elts]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ValueError(f"unsupported expression element: {ast.dump(node)[:60]}")

    return ev(ast.parse(expr.strip(), mode="eval"))


# Factors to a base unit per dimension.
UNITS: dict[str, dict[str, float]] = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "in": 0.0254, "inch": 0.0254,
               "inches": 0.0254, "ft": 0.3048, "foot": 0.3048, "feet": 0.3048, "yd": 0.9144,
               "yard": 0.9144, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344, "nmi": 1852},
    "mass": {"mg": 1e-6, "g": 0.001, "kg": 1, "t": 1000, "tonne": 1000, "oz": 0.0283495,
             "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592, "stone": 6.35029},
    "volume": {"ml": 0.001, "cl": 0.01, "dl": 0.1, "l": 1, "liter": 1, "litre": 1, "m3": 1000,
               "tsp": 0.00492892, "tbsp": 0.0147868, "floz": 0.0295735, "cup": 0.24,
               "pint": 0.473176, "quart": 0.946353, "gal": 3.78541, "gallon": 3.78541},
    "time": {"ms": 0.001, "s": 1, "sec": 1, "min": 60, "h": 3600, "hour": 3600, "hours": 3600,
             "day": 86400, "days": 86400, "week": 604800, "year": 31557600},
    "data": {"b": 1, "kb": 1e3, "mb": 1e6, "gb": 1e9, "tb": 1e12, "kib": 1024, "mib": 1024 ** 2,
             "gib": 1024 ** 3, "tib": 1024 ** 4},
    "speed": {"m/s": 1, "km/h": 1 / 3.6, "kmh": 1 / 3.6, "kph": 1 / 3.6, "mph": 0.44704,
              "knot": 0.514444, "knots": 0.514444},
    "area": {"m2": 1, "km2": 1e6, "ha": 1e4, "acre": 4046.86, "ft2": 0.092903, "sqft": 0.092903},
    "energy": {"j": 1, "kj": 1000, "cal": 4.184, "kcal": 4184, "wh": 3600, "kwh": 3.6e6},
}
TEMPS = {"c": "c", "celsius": "c", "f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}


def convert(value: float, src: str, dst: str) -> float:
    s, d = src.lower().strip().rstrip("."), dst.lower().strip().rstrip(".")
    s, d = s.replace("°", ""), d.replace("°", "")
    if s in TEMPS and d in TEMPS:
        s, d = TEMPS[s], TEMPS[d]
        c = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[s]
        return {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[d]
    for table in UNITS.values():
        if s in table and d in table:
            return value * table[s] / table[d]
    raise ValueError(f"Cannot convert {src} to {dst}.")


class MathAgent(Agent):
    name = "math"
    title = "Math"
    description = "Exact arithmetic, percentages, statistics, unit conversions and date calculations."
    instructions = "Never compute in your head: always use the calculate/convert tools."
    temperature = 0.0

    @tool
    def calculate(self, expression: str) -> str:
        """Evaluate a math expression, e.g. '(15/100)*240', 'sqrt(2)^3', 'mean([3,5,9])'.

        Args:
            expression: The expression to evaluate.
        """
        result = safe_eval(expression)
        if isinstance(result, float) and result.is_integer() and abs(result) < 1e15:
            result = int(result)
        return f"{expression} = {result}"

    @tool
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> str:
        """Convert between units of length, mass, volume, temperature, time, data, speed, area, energy.

        Args:
            value: The amount.
            from_unit: Source unit (e.g. km, lb, F, GB, mph).
            to_unit: Target unit.
        """
        return f"{value:g} {from_unit} = {convert(float(value), from_unit, to_unit):.6g} {to_unit}"

    @tool
    def date_difference(self, start: str, end: str = "today") -> str:
        """Number of days between two dates (YYYY-MM-DD or 'today').

        Args:
            start: First date.
            end: Second date.
        """
        parse = lambda s: dt.date.today() if s.lower() == "today" else dt.date.fromisoformat(s)  # noqa: E731
        days = (parse(end) - parse(start)).days
        return f"{days} days ({days / 7:.1f} weeks, {days / 365.25:.2f} years)"

    @tool
    def add_to_date(self, date: str, days: int = 0, weeks: int = 0) -> str:
        """Add (or subtract with negatives) days/weeks to a date.

        Args:
            date: YYYY-MM-DD or 'today'.
            days: Days to add.
            weeks: Weeks to add.
        """
        base = dt.date.today() if date.lower() == "today" else dt.date.fromisoformat(date)
        result = base + dt.timedelta(days=int(days), weeks=int(weeks))
        return result.strftime("%A %d %B %Y")
