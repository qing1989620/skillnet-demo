"""Independent worker: SKILLNET_WORKER_MODE=external python -m skillnet.worker."""
import os
import threading
import time
import uuid


def acquire_writer_lock(path):
    """Single-host library currently requires exactly one external writer."""
    stream = path.open('a+b')
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        if path.stat().st_size == 0:
            stream.write(b'0');stream.flush();stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    return stream


def execute_job(queue, job, handler):
    owner = job['worker_owner']
    stop = threading.Event()
    def renew():
        while not stop.wait(10):
            if not queue.heartbeat(job['id'], owner):
                break
    renewer = threading.Thread(target=renew, daemon=True)
    renewer.start()
    try:
        handler(job['id'], job['payload'])
        queue.finish(job['id'], owner)
    except Exception as exc:
        queue.finish(job['id'], owner, 'failed', type(exc).__name__)
        raise
    finally:
        stop.set()
        renewer.join(timeout=1)


def main():
    os.environ['SKILLNET_WORKER_MODE'] = 'external'
    import server
    server._startup()
    writer_lock = acquire_writer_lock(server.config.OUT_DIR / 'worker.lock')
    queue = server.job_queue()
    owner = f'{os.getpid()}-{uuid.uuid4().hex[:8]}'
    while True:
        for rid in queue.recover():
            run = server.run_store().load(rid)
            if run and run.status not in server.TERMINAL:
                run.status = 'INTERRUPTED'
                run.error = '执行 worker 租约过期；已保存的步骤与产物可恢复查看，重新运行需新任务预算。'
                run.ended_at_ms = server.now_ms()
                server.run_store().save(run)
        job = queue.claim(owner)
        if not job:
            time.sleep(.5)
            continue
        job['worker_owner'] = owner
        # Refresh persisted learning between jobs; never share mutable library state across workers.
        server.STATE.clear()
        server._startup()
        execute_job(queue, job, lambda rid, payload: server._run_worker(rid, server.RunReq.model_validate(payload)))


if __name__ == '__main__':
    main()
