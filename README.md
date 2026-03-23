

## Start the K8s cluster and deploy Ingress Controler

```shell
uv run invoke do.create
```


## Install Styrmin into the Kubernetes Cluster

```shell
helm upgrade --install styrmin oci://registry.opsmill.io/opsmill/chart/styrmin \
  --create-namespace \
  -n styrmin \
  -f styrmin/values.yaml \
  --wait \
  --timeout 5m
```

## Configure Styrmin
```shell
uv run invoke init-styrmin
```

## Install Drivers and deploy apps

Add Infrahub and Semaphore Drivers
```
uv run styrminctl drivers load-local-version /styrmin/drivers/infrahub
uv run styrminctl drivers load-local-version /styrmin/drivers/semaphore
```

## Initialize both applications

```shell
uv run invoke init-infrahub init-semaphore
```


## Delete the environment

```shell
uv run invoke do.destroy
```

