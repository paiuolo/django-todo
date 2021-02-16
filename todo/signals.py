from django import dispatch


task_completion_toggled = dispatch.Signal(providing_args=["task"])
