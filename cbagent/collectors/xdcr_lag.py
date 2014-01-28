from time import time, sleep
from threading import Thread
from uuid import uuid4

from logger import logger

from cbagent.collectors import Latency
from cbagent.collectors.libstats.pool import Pool

uhex = lambda: uuid4().hex


class XdcrLag(Latency):

    COLLECTOR = "xdcr_lag"

    METRICS = ("xdcr_lag", )

    NUM_THREADS = 10

    def __init__(self, settings):
        super(Latency, self).__init__(settings)

        self.pools = []
        for bucket in self.get_buckets():
            src_pool = Pool(
                bucket=bucket,
                host=settings.master_node,
                username=bucket,
                password=settings.rest_password,
                quiet=True,
            )
            dst_pool = Pool(
                bucket=bucket,
                host=settings.dest_master_node,
                username=bucket,
                password=settings.rest_password,
                quiet=True,
                unlock_gil=False,
            )
            self.pools.append((bucket, src_pool, dst_pool))

    @staticmethod
    def _measure_lags(src_pool, dst_pool):
        src_client = src_pool.get_client()
        dst_client = dst_pool.get_client()

        key = "xdcr_track_{}".format(uhex())

        src_client.set(key, key)
        t0 = time()
        while True:
            r = dst_client.get(key)
            if r.value:
                break
            else:
                sleep(0.05)
        t1 = time()

        src_client.delete(key)

        src_pool.release_client(src_client)
        dst_pool.release_client(dst_client)

        return {"xdcr_lag": (t1 - t0) * 1000}  # s -> ms

    def sample(self):
        while True:
            try:
                for bucket, src_pool, dst_pool in self.pools:
                    lags = self._measure_lags(src_pool, dst_pool)
                    self.store.append(lags,
                                      cluster=self.cluster,
                                      bucket=bucket,
                                      collector=self.COLLECTOR)
            except Exception as e:
                logger.warn(e)

    def collect(self):
        threads = [Thread(target=self.sample) for _ in range(self.NUM_THREADS)]
        map(lambda t: t.start(), threads)
        map(lambda t: t.join(), threads)
