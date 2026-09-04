import concurrent.futures

EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=25,
    thread_name_prefix="MultiConnWorker"
)