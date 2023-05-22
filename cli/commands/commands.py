from functools import partial

commands = {}


class command:
    def __init__(self, name: str = None, help: str = None):
        self._name = name
        self.help = help
        self.arguments = []

    def __call__(self, func):
        self._func = func
        self.__doc__ = func.__doc__
        if self.help is None:
            self.help = self.__doc__.strip().splitlines()[0].strip()
        return self

    def __set_name__(self, owner, name):
        if not name.startswith('cmd_'):
            raise ValueError(f'command methods must start with cmd_ ({name})')
        if self._name is None:
            self._name = name[4:]
        if self._name in commands:
            raise ValueError(f'{name} registered more than once')
        commands[self._name] = self

    def __get__(self, instance, owner=None):
        return partial(self._func, instance)


class argument:
    def __init__(self, *args, **kwargs):
        self._command = None
        self._args = args
        self._kwargs = kwargs

    def __call__(self, func):
        if isinstance(func, command):
            self._command = func
        elif isinstance(func, argument):
            self._command = func._command
        else:
            raise ValueError(f'cannot use `argument` before decorating with `command`')
        self._func = func
        self.__doc__ = func.__doc__
        return self

    def __set_name__(self, owner, name):
        # chain set_names
        self._func.__set_name__(owner, name)
        commands[self._command._name].arguments.append((self._args, self._kwargs))

    def __get__(self, instance, owner=None):
        return partial(self._command._func, instance)