import itertools
import concurrent.futures


class _CallbackHandle():
    def __init__(self, key, id, dispatcher):
        self._key = key
        self._id = id
        self._dispatcher = dispatcher

    def _is_valid(self):
        return self._dispatcher._is_handle_valid(self._key, self._id)

    def remove(self):
        if self._is_valid():
            self._dispatcher._remove_callback(key, id)
        else:
            raise Exception('Callback has already been removed, you cannot remove it twice.')


class _CallbackDispatcher():
    def __init__(self, max_thread_workers=None):
        self._id_gen = itertools.count()
        self._callbacks = dict()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_thread_workers)

    def _add_callback(self, callback, key=None):
        if key not in self._callbacks:
            self._callbacks[key] = dict()
        callback_id = next(self._id_gen)
        self._callbacks[key][id] = callback
        return _CallbackHandle(key, callback_id, self)

    def _remove_callback(self, key, id):
        del self._callbacks[key][id]

    def _run_callbacks(self, key, value):
        funcs_to_run = list(self._callbacks[None].items())
        funcs_to_run.extend(self._callbacks[key].items())
        for f in funcs_to_run:
            self._executor.submit(f, key, value)

    def _is_handle_valid(self, key, id):
        if key not in self._callbacks:
            return False 
        if id not in self._callbacks[key]:
            return False 
        return True

    def _remove_all_callbacks(self, stop_scheduled=True):
        self._executor.shutdown(wait=not stop_scheduled)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_thread_workers)
        self._callbacks = {None: list()}

    def __del__(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

