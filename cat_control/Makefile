.PHONY: lint-fix
lint-fix:
	black --config ../pyproject.toml .
	isort . --resolve-all-configs --config-root .. --skip .venv --skip dax_video --skip dax_artifacts
	flake8 --config ../.flake8 .
	pylint app