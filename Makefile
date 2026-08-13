export PYTHONUTF8=1

.PHONY: up test down

up:
	docker compose up -d
	python scripts/iam_demo.py
	python scripts/vpc_demo.py
	python scripts/s3_demo.py
	python scripts/ec2_demo.py

test:
	pytest -v

down:
	docker compose down
