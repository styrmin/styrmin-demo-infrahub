from invoke import Collection

from . import do
from .semaphore import init_semaphore
from .styrmin import init_styrmin
from .infrahub import init_infrahub

ns = Collection()
ns.add_task(init_semaphore)
ns.add_task(init_styrmin)
ns.add_task(init_infrahub)
ns.add_collection(do.ns)
