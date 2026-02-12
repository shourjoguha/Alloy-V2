#!/usr/bin/env python3
import ast
import sys
from pathlib import Path

def check_response_envelope(route_file: Path) -> list[str]:
    issues = []
    
    with open(route_file) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == 'get' or decorator.func.attr == 'post':
                        if not any(
                            isinstance(d, ast.keyword) and d.arg == 'response_model'
                            for d in decorator.keywords
                        ):
                            issues.append(f"Line {node.lineno}: {node.name} missing response_model")
    
    return issues

def main():
    routes_dir = Path('app/api/routes')
    all_issues = []
    
    for route_file in routes_dir.glob('*.py'):
        if route_file.name == '__init__.py':
            continue
        issues = check_response_envelope(route_file)
        for issue in issues:
            all_issues.append(f"{route_file}: {issue}")
    
    if all_issues:
        print("Contract validation issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("All contracts validated successfully")
        sys.exit(0)

if __name__ == '__main__':
    main()
