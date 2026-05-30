"""Planted security defects for bandit + semgrep."""
import subprocess
import hashlib
import pickle


def run_shell(cmd: str) -> int:
    return subprocess.call(cmd, shell=True)  # bandit B602 / shell injection


def weak_hash(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()  # bandit B324 weak hash


def run_eval(expr: str):
    return eval(expr)  # bandit B307 / dangerous eval


def load_untrusted(data: bytes):
    return pickle.loads(data)  # bandit B301 / insecure deserialization
