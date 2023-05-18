def make_task_thread_func_closure(func, data):
    """Prepare a Gio.TaskThreadFunc with its data bound in a closure"""

    def closure(task, obj, _data, cancellable):
        func(task, obj, data, cancellable)

    return closure
