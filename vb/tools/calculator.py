from __future__ import annotations

import ast
import operator
import re

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Only basic arithmetic is allowed.")


def extract_expression(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(\d)\s*[x×]\s*(\d)", r"\1 * \2", text)
    text = text.replace("÷", "/")
    match = re.search(r"[\d(][\d\s+\-*/().]+[\d)]", text)
    if not match:
        raise ValueError("I could not find a calculation.")
    return match.group(0)


def calculate(text: str) -> str:
    expr = extract_expression(text)
    tree = ast.parse(expr, mode="eval")
    result = _eval(tree)
    if result.is_integer():
        return f"{expr} = {int(result)}"
    return f"{expr} = {result}"
