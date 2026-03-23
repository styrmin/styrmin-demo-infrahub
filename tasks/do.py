import json
import os

from invoke import Collection, Context, task

DO_INSTANCE_SIZE = os.getenv("DO_INSTANCE_SIZE", "g-4vcpu-16gb")
DO_PREFIX = os.getenv("DO_PREFIX", "")
DO_REGION = os.getenv("DO_REGION", "ams3")
DO_FRONT_LB_ID = os.getenv("DO_FRONT_LB_ID", "00000000-0000-0000-0000-000000000000")


@task(name="create-cluster")
def create_cluster(context: Context) -> None:
    """Create a new DigitalOcean Kubernetes cluster."""
    # TODO: replace with actual command
    command1 = f"""
    doctl kubernetes cluster create {DO_PREFIX}styrmin-demo \
        --region {DO_REGION} \
        --version 1.35.1-do.0 \
        --node-pool "name=worker-pool;size={DO_INSTANCE_SIZE};count=2"
    """
    context.run(command1, pty=True)

@task(name="setup-ingress")
def setup_ingress(context: Context) -> None:
    command2 = f"""
    helm repo add traefik https://traefik.github.io/charts
    helm repo update
    helm upgrade --install traefik traefik/traefik \
        --create-namespace \
        -n styrmin \
        --set service.annotations."kubernetes\\.digitalocean\\.com/load-balancer-id"={DO_FRONT_LB_ID} \
        --set ingressClass.enabled=false \
        --set rbac.namespaced=true \
        --wait \
        --timeout 3m \
        --skip-crds
    """
    context.run(command2, pty=True)


@task(name="create")
def create(context: Context) -> None:
    """Create a new DigitalOcean Kubernetes cluster."""

    create_cluster(context)
    setup_ingress(context)


@task(name="destroy")
def destroy(context: Context) -> None:
    """Destroy the DigitalOcean Kubernetes cluster and its associated volumes."""
    cluster_name = f"{DO_PREFIX}styrmin-demo"

    result = context.run(
        f"doctl kubernetes cluster list-associated-resources {cluster_name} --output json",
        hide=True,
    )
    resources = json.loads(result.stdout)
    volume_ids = [v["id"] for v in resources.get("volumes", [])]

    cmd = f"doctl kubernetes cluster delete-selective {cluster_name} --force"
    if volume_ids:
        cmd += f" --volumes {','.join(volume_ids)}"

    context.run(cmd, pty=True)

ns = Collection("do")
ns.add_task(create)
ns.add_task(setup_ingress)
ns.add_task(create_cluster)
ns.add_task(destroy)
