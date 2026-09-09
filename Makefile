.PHONY: test demo lint knowledge benchmark

test:
	python -m pytest -q

demo:
	python -m occupational_fitness_rag.commands demo

lint:
	python -m ruff check src tests scripts examples
	python -m ruff format --check src tests scripts examples

knowledge:
	python -m occupational_fitness_rag.commands build-knowledge

benchmark:
	python -m occupational_fitness_rag.commands benchmark
