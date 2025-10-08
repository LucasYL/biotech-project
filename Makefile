# 文件用途 / Purpose:
#   中文：提供常用构建与运行指令的占位 Makefile。
#   English: Placeholder Makefile providing common build and run targets.

.PHONY: all lint test download-data dashboard

all:
	@echo "[TODO] Implement pipeline orchestration in Makefile"

lint:
	@echo "[TODO] Add linting commands"

test:
	@echo "[TODO] Run pytest once tests are implemented"

download-data:
	@echo "[TODO] Hook scripts/download_example_data.py"

dashboard:
	@echo "[TODO] streamlit run dashboard/app.py"
