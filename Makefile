# AIPy 项目 Makefile
.PHONY: help install test test-unit test-integration test-cov clean lint format

help:  ## 显示帮助信息
	@echo "AIPy 项目命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## 安装项目和依赖
	pip install -e .

install-dev:  ## 安装开发依赖
	pip install -e .[dev]

install-test:  ## 安装测试依赖
	pip install -e .[test]

test:  ## 运行所有测试
	pytest

test-unit:  ## 仅运行单元测试
	pytest -m unit

test-integration:  ## 仅运行集成测试
	pytest -m integration

test-cov:  ## 运行测试并生成覆盖率报告
	pytest --cov=aipyapp --cov-report=html --cov-report=term

test-fast:  ## 运行快速测试（排除慢速测试）
	pytest -m "not slow"

test-parallel:  ## 并行运行测试
	pytest -n auto

test-verbose:  ## 详细模式运行测试
	pytest -vvs

test-watch:  ## 监视模式运行测试（需要 pytest-watch）
	@command -v ptw >/dev/null 2>&1 || { echo "请先安装 pytest-watch: pip install pytest-watch"; exit 1; }
	ptw -- -x

lint:  ## 运行代码检查
	ruff check aipyapp tests

format:  ## 格式化代码
	ruff format aipyapp tests

clean:  ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true

build:  ## 构建项目
	python -m build

docs:  ## 生成文档（如果有 sphinx）
	@echo "文档生成功能待实现"

check-all: lint test  ## 运行所有检查（lint + test）

pre-commit: format lint test-fast  ## 提交前检查

ci: clean install-test lint test-cov  ## CI 流程