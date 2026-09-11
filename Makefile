SRC_DIR		= src
TEST_DIR	= tests
CHECK_DIRS 	= $(SRC_DIR) $(TEST_DIR)
PACKAGE_DIR = $(SRC_DIR)/personio_hacking
PYTEST_FLAGS = -vv


.PHONY: check
check: format-check lint type-check test

.PHONY: format
format: ## Format repository code
	uv run ruff format $(CHECK_DIRS)
	uv run ruff check --select I001 --fix $(CHECK_DIRS)

.PHONY: format-check
format-check: ## Check the code format with no actual side effects
	uv run ruff format --check $(CHECK_DIRS)
	uv run ruff check --select I001 $(CHECK_DIRS)

.PHONY: lint
lint: ## Launch the linting tool
	uv run ruff check $(SRC_DIR) $(TEST_DIR)

.PHONY: type-check
type-check: ## Launch the type checking tool
	uv run pyrefly check $(SRC_DIR)

.PHONY: test
test: ## Launch the tests
	uv run pytest $(PYTEST_FLAGS) $(TEST_DIR)

.PHONY: install
install: ## Install dependencies using uv
	uv sync

.PHONY: help
help: ## Show the available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'