# task.py
#
# Copyright 2023 Geoffrey Coulaud
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from functools import wraps

from gi.repository import Gio


def create_task_thread_func_closure(func, data):
    """Wrap a Gio.TaskThreadFunc with the given data in a closure"""

    def closure(task, source_object, _data, cancellable):
        func(task, source_object, data, cancellable)

    return closure


def decorate_set_task_data(task):
    """Decorate Gio.Task.set_task_data to replace it"""

    def decorator(original_method):
        @wraps(original_method)
        def new_method(task_data):
            task.task_data = task_data

        return new_method

    return decorator


def decorate_run_in_thread(task):
    """Decorate Gio.Task.run_in_thread to pass the task data correctly
    Creates a closure around task_thread_func with the task data available."""

    def decorator(original_method):
        @wraps(original_method)
        def new_method(task_thread_func):
            closure = create_task_thread_func_closure(task_thread_func, task.task_data)
            original_method(closure)

        return new_method

    return decorator


# pylint: disable=too-few-public-methods
class Task:
    """Wrapper around Gio.Task to patch task data not being passed"""

    @classmethod
    def new(cls, source_object, cancellable, callback, callback_data):
        """Create a new, monkey-patched Gio.Task.
        The `set_task_data` and `run_in_thread` methods are decorated.

        As of 2023-05-19, pygobject does not work well with Gio.Task, so to pass data
        the only viable way it to create a closure with the thread function and its data.
        This class is supposed to make Gio.Task comply with its expected behaviour
        per the docs:

        http://lazka.github.io/pgi-docs/#Gio-2.0/classes/Task.html#Gio.Task.set_task_data

        This code may break if pygobject overrides change in the future.
        We need to manually pass `self` to the decorators since it's otherwise bound but
        not accessible from Python's side.
        """

        task = Gio.Task.new(source_object, cancellable, callback, callback_data)
        task.set_task_data = decorate_set_task_data(task)(task.set_task_data)
        task.run_in_thread = decorate_run_in_thread(task)(task.run_in_thread)
        return task
