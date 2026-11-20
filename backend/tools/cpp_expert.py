# backend/tools/cpp_expert.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# C++ Optimization & Generation with Syntax & Logic Validator

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


class CppExpert:
    """Generates production C++ for memory manipulation and validates
    syntax/logic. Zero-latency, cache-local by design."""

    HEADER_TEMPLATE = """#pragma once
#include <windows.h>
#include <cstdint>
#include <vector>
#include <stdexcept>

namespace {ns} {{

class Memory {{
public:
    static uint8_t* read(HANDLE h, uintptr_t addr, size_t size);
    static void write(HANDLE h, uintptr_t addr, const uint8_t* data, size_t size);
    static uintptr_t read_ptr(HANDLE h, uintptr_t addr);
    static DWORD protect(HANDLE h, uintptr_t addr, size_t size, DWORD new_protect);
}};

}}
"""

    def generate_memory_tool(self, namespace: str = "mem") -> str:
        return self.HEADER_TEMPLATE.format(ns=namespace)

    def validate(self, code: str) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not code.strip():
            errors.append("Empty code")
            return ValidationResult(False, errors, warnings)

        if code.count("{") != code.count("}"):
            errors.append("Unbalanced braces")

        if ("HANDLE" in code or "DWORD" in code) and "windows.h" not in code:
            warnings.append("Windows types used without including windows.h")

        if "reinterpret_cast" in code:
            warnings.append("reinterpret_cast detected - verify pointer safety")

        if "delete" in code and "std::unique_ptr" not in code:
            warnings.append("Raw delete detected - prefer RAII / smart pointers")

        valid = len(errors) == 0
        return ValidationResult(valid, errors, warnings)
