import os
from pathlib import Path
import sys

import time
import httpx
from invoke import Context, task

@task(name="init-infrahub")
def init_infrahub(
    context: Context,
) -> None:
    PREFIX = "[init-infrahub]"

    command = "uv run infrahubctl schema load schemas"
    print(f"{PREFIX} Loading Schemas...")
    context.run(command, pty=True)

    command = "uv run infrahubctl object load objects"
    print(f"{PREFIX} Loading Objects...")
    context.run(command, pty=True)
