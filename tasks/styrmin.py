
import os
from pathlib import Path
import sys

import time
import httpx
from invoke import Context, task

DO_PREFIX = os.getenv("DO_PREFIX")
DO_REGION = os.getenv("DO_REGION")
ACCESS_KEY_ID=os.getenv("ACCESS_KEY_ID")
SECRET_ACCESS_KEY=os.getenv("SECRET_ACCESS_KEY")
DO_APPS_LB_ID = os.getenv("DO_APPS_LB_ID")
DO_S3_BACKUP_NAME = os.getenv("DO_S3_BACKUP_NAME", f"{DO_PREFIX}styrmin-backup")
STYRMIN_SERVER_ADDRESS = os.getenv("STYRMIN_SERVER_ADDRESS", "")

STYRMIN_CLUSTER_NAME = os.getenv("STYRMIN_CLUSTER_NAME", "demo")
STYRMIN_ENV_NAME = os.getenv("STYRMIN_ENV_NAME", "dga-demo")


def get_cluster_id(name: str, server_address: str = STYRMIN_SERVER_ADDRESS) -> str:
    """Look up a Styrmin cluster ID by name."""
    query = "query ListClusters { clusters { id name config } }"
    response = httpx.post(f"{server_address}/graphql", json={"query": query})
    response.raise_for_status()
    clusters = response.json()["data"]["clusters"]
    for cluster in clusters:
        if cluster["name"] == name:
            return cluster["id"]
    raise ValueError(f"Cluster {name!r} not found")


def get_environment_id(name: str, server_address: str = STYRMIN_SERVER_ADDRESS) -> str:
    """Look up a Styrmin environment ID by name."""
    query = "query ListEnvironments { environments { id name config cluster { id name } backupStorageLocation { id name } } }"
    response = httpx.post(f"{server_address}/graphql", json={"query": query})
    response.raise_for_status()
    environments = response.json()["data"]["environments"]
    for env in environments:
        if env["name"] == name:
            return env["id"]
    raise ValueError(f"Environment {name!r} not found")


def get_environment_bsl(name: str, server_address: str = STYRMIN_SERVER_ADDRESS) -> str | None:
    """Look up the backup storage location assigned to an environment. Returns BSL id or None."""
    query = "query ListEnvironments { environments { id name backupStorageLocation { id name } } }"
    response = httpx.post(f"{server_address}/graphql", json={"query": query})
    response.raise_for_status()
    environments = response.json()["data"]["environments"]
    for env in environments:
        if env["name"] == name:
            bsl = env.get("backupStorageLocation")
            return bsl["id"] if bsl else None
    raise ValueError(f"Environment {name!r} not found")


def get_backup_storage_location_id(name: str, server_address: str = STYRMIN_SERVER_ADDRESS) -> str:
    """Look up a Styrmin backup storage location ID by name."""
    query = "query ListBackupStorageLocations { backupStorageLocations { id name endpoint bucket region } }"
    response = httpx.post(f"{server_address}/graphql", json={"query": query})
    response.raise_for_status()
    locations = response.json()["data"]["backupStorageLocations"]
    for location in locations:
        if location["name"] == name:
            return location["id"]
    raise ValueError(f"Backup storage location {name!r} not found")


@task(name="init-styrmin")
def init_styrmin(
    context: Context,
) -> None:
    PREFIX = "[init-styrmin]"

    # --- Cluster ---
    try:
        cluster_id = get_cluster_id(STYRMIN_CLUSTER_NAME)
        print(f"{PREFIX} Cluster {STYRMIN_CLUSTER_NAME!r} already exists (id: {cluster_id})")
    except ValueError:
        print(f"{PREFIX} Creating cluster {STYRMIN_CLUSTER_NAME!r}...")
        command = """
        uv run styrminctl clusters create %s \
        -c '{"fqdn_suffix": "styrmin.io", "standard_storage": {"storage_class": "do-block-storage"}}'
        """ % (STYRMIN_CLUSTER_NAME)
        context.run(command, pty=True)
        cluster_id = get_cluster_id(STYRMIN_CLUSTER_NAME)
        print(f"{PREFIX} Cluster {STYRMIN_CLUSTER_NAME!r} created (id: {cluster_id})")

    # --- Environment ---
    try:
        environment_id = get_environment_id(STYRMIN_ENV_NAME)
        print(f"{PREFIX} Environment {STYRMIN_ENV_NAME!r} already exists (id: {environment_id})")
    except ValueError:
        print(f"{PREFIX} Creating environment {STYRMIN_ENV_NAME!r}...")
        command = """
        uv run styrminctl environments create %s %s \
        -c '{"ip_whitelist": ["0.0.0.0/0"], "dedicated_ingress": {"service": {"annotations": {"kubernetes.digitalocean.com/load-balancer-id": "%s"}}}}'
        """ % (STYRMIN_ENV_NAME, cluster_id, DO_APPS_LB_ID)
        context.run(command, pty=True)
        environment_id = get_environment_id(STYRMIN_ENV_NAME)
        print(f"{PREFIX} Environment {STYRMIN_ENV_NAME!r} created (id: {environment_id})")

    # --- Backup Storage Location ---
    try:
        bsl_id = get_backup_storage_location_id("do-spaces")
        print(f"{PREFIX} Backup storage location 'do-spaces' already exists (id: {bsl_id})")
    except ValueError:
        print(f"{PREFIX} Creating backup storage location 'do-spaces'...")
        command = f"""
        uv run styrminctl backup-locations create do-spaces \
            --endpoint https://{DO_REGION}.digitaloceanspaces.com \
            --bucket {DO_S3_BACKUP_NAME} \
            --region {DO_REGION} \
            --access-key-id {ACCESS_KEY_ID} \
            --secret-access-key {SECRET_ACCESS_KEY}
        """
        context.run(command, pty=True)
        bsl_id = get_backup_storage_location_id("do-spaces")
        print(f"{PREFIX} Backup storage location 'do-spaces' created (id: {bsl_id})")

    # --- BSL Assignment ---
    existing_bsl = get_environment_bsl(STYRMIN_ENV_NAME)
    if existing_bsl:
        print(f"{PREFIX} Backup storage location already assigned to environment {STYRMIN_ENV_NAME!r} (bsl id: {existing_bsl})")
    else:
        print(f"{PREFIX} Assigning backup storage location 'do-spaces' to environment {STYRMIN_ENV_NAME!r}...")
        command = f"""
        uv run styrminctl backup-locations assign {environment_id} {bsl_id}
        """
        context.run(command, pty=True)
        print(f"{PREFIX} Backup storage location 'do-spaces' assigned to environment {STYRMIN_ENV_NAME!r}")