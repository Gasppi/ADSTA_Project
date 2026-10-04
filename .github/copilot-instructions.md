# Repository Guidelines - ADSTA Project

## Project Overview
This repository contains a Credit Risk Scoring System built for the Applied Data Sciences Toolkits and Architectures course at the University of Lucerne.

## Tech Stack & Tooling
- Python 3.13
- Package manager: `uv`
- Version control: Git / GitHub

## Code & Architecture Standards
- Follow PEP 8 style guide for Python code.
- Keep functions modular, type-hinted, and well-documented.
- Always use explicit exceptions and clean logging instead of bare `print()` statements.
- Write unit tests for new business logic under `tests/`.

## Agent Workflow Rules
- Propose concise and clear plans before generating large code changes.
- Never edit files outside the specified scope of the task.
- Ensure all introduced features maintain backward compatibility with existing APIs.

## Setup & Verification Commands
- Install dependencies: `uv sync`
- Run tests: `uv run pytest`
- Run these after every change and fix failures before finishing.
