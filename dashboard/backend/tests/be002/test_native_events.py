from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "dashboard" / "backend" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_dev_flow_dashboard.snapshot.events import (
    WatchRequest,
    WindowsDirectoryEventSource,
)
from ai_dev_flow_dashboard.snapshot.watcher import PollingWatcher


@unittest.skipUnless(os.name == "nt", "Windows native directory notifications")
class WindowsDirectoryEventSourceTests(unittest.TestCase):
    def test_atomic_replace_emits_event_and_stop_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = threading.Event()
            source = WindowsDirectoryEventSource()
            source.start((root,), changed.set)
            temporary = root / ".value.tmp"
            target = root / "value.txt"
            temporary.write_text("changed\n", encoding="utf-8")
            os.replace(temporary, target)
            self.assertTrue(changed.wait(2))

            started = time.monotonic()
            source.stop()
            self.assertLess(time.monotonic() - started, 1.0)

    def test_update_arms_added_root_and_stops_removed_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            changed = threading.Event()
            source = WindowsDirectoryEventSource()
            source.start((first,), changed.set)
            removed_thread = source._watches[first.resolve()].thread
            source.update((second,))
            self.assertIsNotNone(removed_thread)
            self.assertFalse(removed_thread.is_alive())
            self.assertNotIn(first.resolve(), source._watches)

            changed.clear()
            (first / "ignored.txt").write_text("old root\n", encoding="utf-8")
            self.assertFalse(changed.wait(0.2))

            (second / "observed.txt").write_text("new root\n", encoding="utf-8")
            self.assertTrue(changed.wait(2))
            source.stop()
            self.assertEqual({}, source._watches)

    def test_start_returns_only_after_kernel_read_is_registered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            entered = threading.Event()
            release = threading.Event()

            class DelayedRegistration:
                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def ReadDirectoryChangesW(self, *args):
                    entered.set()
                    if not release.wait(2):
                        raise TimeoutError("test did not release native registration")
                    return real_kernel32.ReadDirectoryChangesW(*args)

            errors = []

            def start_source():
                try:
                    source.start((root,), lambda: None)
                except BaseException as exc:
                    errors.append(exc)

            source._kernel32 = DelayedRegistration()
            starter = threading.Thread(target=start_source)
            starter.start()
            self.assertTrue(entered.wait(1))
            self.assertTrue(starter.is_alive())
            release.set()
            starter.join(2)
            self.assertFalse(starter.is_alive())
            self.assertEqual([], errors)
            source.stop()

    def test_remove_during_callback_does_not_rearm_pending_io(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            callback_entered = threading.Event()
            release_callback = threading.Event()
            errors = []

            def callback():
                callback_entered.set()
                release_callback.wait(2)

            source = WindowsDirectoryEventSource()
            source.start((root,), callback)
            (root / "value.txt").write_text("changed\n", encoding="utf-8")
            self.assertTrue(callback_entered.wait(2))

            def remove_root():
                try:
                    source.update(())
                except BaseException as exc:
                    errors.append(exc)

            remover = threading.Thread(target=remove_root)
            remover.start()
            time.sleep(0.05)
            self.assertTrue(remover.is_alive())
            release_callback.set()
            remover.join(2)
            self.assertFalse(remover.is_alive())
            self.assertEqual([], errors)
            self.assertEqual({}, source._watches)

    def test_thread_start_failure_cancels_and_drains_registered_io(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32

            class RecordingKernel:
                def __init__(self):
                    self.cancel_calls = 0
                    self.blocking_result_calls = 0

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CancelIoEx(self, *args):
                    self.cancel_calls += 1
                    return real_kernel32.CancelIoEx(*args)

                def GetOverlappedResult(self, *args):
                    if args[-1]:
                        self.blocking_result_calls += 1
                    return real_kernel32.GetOverlappedResult(*args)

            recording = RecordingKernel()
            source._kernel32 = recording
            with mock.patch.object(
                threading.Thread,
                "start",
                side_effect=RuntimeError("thread start failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "thread start failed"):
                    source.start((root,), lambda: None)
            self.assertGreaterEqual(recording.cancel_calls, 1)
            self.assertGreaterEqual(recording.blocking_result_calls, 1)
            self.assertEqual({}, source._watches)

    def test_non_recursive_request_ignores_nested_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            changed = threading.Event()
            source = WindowsDirectoryEventSource()
            source.start((WatchRequest(root, False),), changed.set)
            (nested / "ignored.txt").write_text("nested\n", encoding="utf-8")
            self.assertFalse(changed.wait(0.2))
            (root / "observed.txt").write_text("top-level\n", encoding="utf-8")
            self.assertTrue(changed.wait(2))
            source.stop()

    def test_rearmed_read_is_drained_when_remove_wins_before_next_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            rearmed = threading.Event()
            release_rearm = threading.Event()

            class RearmBarrierKernel:
                def __init__(self):
                    self.read_calls = 0
                    self.result_calls = 0

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def ReadDirectoryChangesW(self, *args):
                    self.read_calls += 1
                    result = real_kernel32.ReadDirectoryChangesW(*args)
                    if self.read_calls == 2:
                        rearmed.set()
                        release_rearm.wait(2)
                    return result

                def GetOverlappedResult(self, *args):
                    self.result_calls += 1
                    return real_kernel32.GetOverlappedResult(*args)

            barrier = RearmBarrierKernel()
            source._kernel32 = barrier
            source.start((root,), lambda: None)
            (root / "value.txt").write_text("changed\n", encoding="utf-8")
            self.assertTrue(rearmed.wait(2))

            remover = threading.Thread(target=source.update, args=((),))
            remover.start()
            time.sleep(0.05)
            release_rearm.set()
            remover.join(2)
            self.assertFalse(remover.is_alive())
            self.assertGreaterEqual(barrier.result_calls, 2)
            self.assertEqual({}, source._watches)

    def test_wait_failure_is_drained_before_handles_are_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32

            class WaitFailureKernel:
                def __init__(self):
                    self.cancel_calls = 0
                    self.result_calls = 0

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def WaitForSingleObject(self, *args):
                    ctypes.set_last_error(6)
                    return 0xFFFFFFFF

                def CancelIoEx(self, *args):
                    self.cancel_calls += 1
                    return real_kernel32.CancelIoEx(*args)

                def GetOverlappedResult(self, *args):
                    self.result_calls += 1
                    return real_kernel32.GetOverlappedResult(*args)

            recording = WaitFailureKernel()
            source._kernel32 = recording
            source.start((root,), lambda: None)
            watch = source._watches[root.resolve()]
            watch.thread.join(2)
            self.assertFalse(watch.thread.is_alive())
            self.assertIsInstance(source.failure, OSError)
            self.assertEqual(0, recording.result_calls)

            source.stop()

            self.assertGreaterEqual(recording.cancel_calls, 1)
            self.assertEqual(1, recording.result_calls)
            self.assertEqual({}, source._watches)

    def test_concurrent_update_and_stop_close_each_handle_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            close_started = threading.Event()
            release_close = threading.Event()

            class CloseBarrierKernel:
                def __init__(self):
                    self.closed = []
                    self.lock = threading.Lock()

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CloseHandle(self, handle):
                    close_started.set()
                    release_close.wait(2)
                    with self.lock:
                        self.closed.append(int(handle))
                    return real_kernel32.CloseHandle(handle)

            recording = CloseBarrierKernel()
            source._kernel32 = recording
            source.start((root,), lambda: None)

            updater = threading.Thread(target=source.update, args=((),))
            stopper = threading.Thread(target=source.stop)
            updater.start()
            self.assertTrue(close_started.wait(2))
            stopper.start()
            time.sleep(0.05)
            release_close.set()
            updater.join(2)
            stopper.join(2)

            self.assertFalse(updater.is_alive())
            self.assertFalse(stopper.is_alive())
            self.assertEqual(2, len(recording.closed))
            self.assertEqual(2, len(set(recording.closed)))
            self.assertEqual({}, source._watches)
            self.assertEqual({}, source._closing)

    def test_start_waits_for_concurrent_stop_before_rearming(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            close_started = threading.Event()
            release_close = threading.Event()

            class CloseBarrierKernel:
                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CloseHandle(self, handle):
                    close_started.set()
                    release_close.wait(2)
                    return real_kernel32.CloseHandle(handle)

            source._kernel32 = CloseBarrierKernel()
            source.start((root,), lambda: None)
            stopper = threading.Thread(target=source.stop)
            starter = threading.Thread(
                target=source.start,
                args=((root,), lambda: None),
            )
            stopper.start()
            self.assertTrue(close_started.wait(2))
            starter.start()
            time.sleep(0.05)
            release_close.set()
            stopper.join(2)
            starter.join(2)

            watch = source._watches[root.resolve()]
            self.assertFalse(stopper.is_alive())
            self.assertFalse(starter.is_alive())
            self.assertFalse(source._stop.is_set())
            self.assertFalse(watch.stopping.is_set())
            self.assertTrue(watch.thread.is_alive())
            source.stop()

    def test_stop_timeout_prevents_inflight_add_from_registering_late(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource(arm_timeout=0.05)
            real_kernel32 = source._kernel32
            read_started = threading.Event()
            release_read = threading.Event()

            class ReadBarrierKernel:
                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def ReadDirectoryChangesW(self, *args):
                    read_started.set()
                    release_read.wait(2)
                    return real_kernel32.ReadDirectoryChangesW(*args)

            source._kernel32 = ReadBarrierKernel()
            errors = []

            def add_root():
                try:
                    source.update((root,))
                except BaseException as exc:
                    errors.append(exc)

            updater = threading.Thread(target=add_root)
            updater.start()
            self.assertTrue(read_started.wait(2))
            with self.assertRaisesRegex(
                TimeoutError,
                "directory watchers are still starting",
            ):
                source.stop()
            release_read.set()
            updater.join(2)

            self.assertFalse(updater.is_alive())
            self.assertEqual([], errors)
            self.assertEqual({}, source._watches)
            self.assertEqual(set(), source._adding)
            source.stop()

    def test_remove_waits_until_inflight_watch_start_has_one_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            real_thread_start = threading.Thread.start
            watch_start_entered = threading.Event()
            release_watch_start = threading.Event()
            errors = []

            class RecordingKernel:
                def __init__(self):
                    self.closed = []
                    self.lock = threading.Lock()

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CloseHandle(self, handle):
                    with self.lock:
                        self.closed.append(int(handle))
                    return real_kernel32.CloseHandle(handle)

            recording = RecordingKernel()
            source._kernel32 = recording

            def delayed_start(thread):
                if thread.name.startswith("dashboard-directory-events-"):
                    watch_start_entered.set()
                    release_watch_start.wait(2)
                return real_thread_start(thread)

            def update(paths):
                try:
                    source.update(paths)
                except BaseException as exc:
                    errors.append(exc)

            adder = threading.Thread(target=update, args=((root,),))
            remover = threading.Thread(target=update, args=((),))
            with mock.patch.object(threading.Thread, "start", delayed_start):
                adder.start()
                self.assertTrue(watch_start_entered.wait(2))
                remover.start()
                time.sleep(0.05)
                self.assertTrue(remover.is_alive())
                self.assertEqual({}, source._watches)
                release_watch_start.set()
                adder.join(2)
                remover.join(2)

            self.assertFalse(adder.is_alive())
            self.assertFalse(remover.is_alive())
            self.assertEqual([], errors)
            self.assertEqual({}, source._watches)
            self.assertEqual(2, len(recording.closed))
            self.assertEqual(2, len(set(recording.closed)))

    def test_remove_after_inflight_watch_start_failure_does_not_double_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            real_thread_start = threading.Thread.start
            watch_start_entered = threading.Event()
            release_watch_start = threading.Event()
            errors = []

            class RecordingKernel:
                def __init__(self):
                    self.closed = []
                    self.lock = threading.Lock()

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CloseHandle(self, handle):
                    with self.lock:
                        self.closed.append(int(handle))
                    return real_kernel32.CloseHandle(handle)

            recording = RecordingKernel()
            source._kernel32 = recording

            def failing_start(thread):
                if thread.name.startswith("dashboard-directory-events-"):
                    watch_start_entered.set()
                    release_watch_start.wait(2)
                    raise RuntimeError("thread start failed")
                return real_thread_start(thread)

            def update(paths):
                try:
                    source.update(paths)
                except BaseException as exc:
                    errors.append(exc)

            adder = threading.Thread(target=update, args=((root,),))
            remover = threading.Thread(target=update, args=((),))
            with mock.patch.object(threading.Thread, "start", failing_start):
                adder.start()
                self.assertTrue(watch_start_entered.wait(2))
                remover.start()
                time.sleep(0.05)
                self.assertTrue(remover.is_alive())
                self.assertEqual({}, source._watches)
                release_watch_start.set()
                adder.join(2)
                remover.join(2)

            self.assertFalse(adder.is_alive())
            self.assertFalse(remover.is_alive())
            self.assertEqual(1, len(errors))
            self.assertRegex(str(errors[0]), "thread start failed")
            self.assertEqual({}, source._watches)
            self.assertEqual(2, len(recording.closed))
            self.assertEqual(2, len(set(recording.closed)))

    def test_active_operation_aborted_rearms_and_observes_next_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = threading.Event()
            rearmed = threading.Event()
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32

            class RecordingKernel:
                def __init__(self):
                    self.read_calls = 0

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def ReadDirectoryChangesW(self, *args):
                    self.read_calls += 1
                    result = real_kernel32.ReadDirectoryChangesW(*args)
                    if self.read_calls >= 2:
                        rearmed.set()
                    return result

            recording = RecordingKernel()
            source._kernel32 = recording
            source.start((root,), changed.set)
            watch = source._watches[root.resolve()]

            self.assertTrue(
                source._kernel32.CancelIoEx(
                    watch.handle,
                    ctypes.byref(watch.overlapped),
                )
            )
            self.assertTrue(rearmed.wait(2))
            (root / "after-abort.txt").write_text("changed\n", encoding="utf-8")
            self.assertTrue(changed.wait(2))
            self.assertIsNone(source.failure)
            self.assertGreaterEqual(recording.read_calls, 2)
            source.stop()

    def test_stop_closes_watch_after_publish_before_add_returns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32
            real_add_reserved = source._add_reserved
            add_reserved_returned = threading.Event()
            release_add = threading.Event()
            errors = []
            stop_errors = []
            published_threads = []

            class RecordingKernel:
                def __init__(self):
                    self.closed = []
                    self.lock = threading.Lock()

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def CloseHandle(self, handle):
                    with self.lock:
                        self.closed.append(int(handle))
                    return real_kernel32.CloseHandle(handle)

            recording = RecordingKernel()
            source._kernel32 = recording

            def delayed_return(path, *, recursive):
                real_add_reserved(path, recursive=recursive)
                published_threads.append(source._watches[path].thread)
                add_reserved_returned.set()
                release_add.wait(2)

            source._add_reserved = delayed_return

            def update_root():
                try:
                    source.update((root,))
                except BaseException as exc:
                    errors.append(exc)

            updater = threading.Thread(target=update_root)
            updater.start()
            self.assertTrue(add_reserved_returned.wait(2))
            self.assertEqual(set(), source._adding)

            def stop_source():
                try:
                    source.stop()
                except BaseException as exc:
                    stop_errors.append(exc)

            stopper = threading.Thread(target=stop_source)
            stopper.start()
            try:
                stopper.join(1)
                self.assertFalse(stopper.is_alive())
                self.assertTrue(updater.is_alive())
                self.assertEqual([], stop_errors)
                self.assertEqual({}, source._watches)
            finally:
                release_add.set()
            updater.join(2)
            stopper.join(2)

            self.assertFalse(updater.is_alive())
            self.assertFalse(stopper.is_alive())
            self.assertEqual([], errors)
            self.assertEqual([], stop_errors)
            self.assertEqual({}, source._watches)
            self.assertEqual(set(), source._adding)
            self.assertEqual(1, len(published_threads))
            self.assertFalse(published_threads[0].is_alive())
            self.assertEqual(2, len(recording.closed))
            self.assertEqual(2, len(set(recording.closed)))

    def test_notify_overflow_rearm_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failure_reported = threading.Event()
            source = WindowsDirectoryEventSource()
            real_kernel32 = source._kernel32

            class OverflowThenRearmFailureKernel:
                def __init__(self):
                    self.reset_calls = 0
                    self.result_calls = 0

                def __getattr__(self, name):
                    return getattr(real_kernel32, name)

                def ResetEvent(self, handle):
                    self.reset_calls += 1
                    if self.reset_calls == 2:
                        ctypes.set_last_error(6)
                        return 0
                    return real_kernel32.ResetEvent(handle)

                def GetOverlappedResult(self, *args):
                    self.result_calls += 1
                    result = real_kernel32.GetOverlappedResult(*args)
                    if self.result_calls == 1:
                        ctypes.set_last_error(source._ERROR_NOTIFY_ENUM_DIR)
                        return 0
                    return result

            source._kernel32 = OverflowThenRearmFailureKernel()

            def callback():
                if source.failure is not None:
                    failure_reported.set()

            source.start((root,), callback)
            (root / "overflow.txt").write_text("changed\n", encoding="utf-8")
            self.assertTrue(failure_reported.wait(2))
            self.assertIsInstance(source.failure, OSError)
            watch = source._watches[root.resolve()]
            watch.thread.join(2)
            self.assertFalse(watch.thread.is_alive())
            source.stop()

    def test_new_top_level_directory_is_armed_for_later_nested_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            class Coordinator:
                project_root = root
                watch_roots = (root,)
                watch_paths = ()
                watch_excluded_roots = ()

                def __init__(self):
                    self.refresh_count = 0
                    self.state = "starting"

                def refresh(self):
                    self.refresh_count += 1

                def set_watcher_state(self, state):
                    self.state = state

            coordinator = Coordinator()
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.01,
                debounce_seconds=0.02,
                max_wait_seconds=0.1,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(2))
            initial = coordinator.refresh_count
            created = root / "created"
            created.mkdir()
            deadline = time.monotonic() + 2
            while coordinator.refresh_count == initial and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertGreater(coordinator.refresh_count, initial)
            after_directory = coordinator.refresh_count
            (created / "nested.txt").write_text("changed\n", encoding="utf-8")
            deadline = time.monotonic() + 2
            while (
                coordinator.refresh_count == after_directory
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            watcher.stop()
            self.assertGreater(coordinator.refresh_count, after_directory)


if __name__ == "__main__":
    unittest.main()
