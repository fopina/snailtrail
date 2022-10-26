import time
from functools import cached_property


class cached_property_with_ttl(cached_property):
    """
    >>> class A:
    ...     @cached_property_with_ttl(300)
    ...     def expensive(self):
    ...         print('CACHE MISS')
    ...         return 2
    ...
    >>> import time
    >>> time.time = lambda: 0
    >>> a = A()
    >>> a.expensive
    CACHE MISS
    2
    >>> a.expensive
    2
    >>> time.time = lambda: 200
    >>> a.expensive
    2
    >>> time.time = lambda: 400
    >>> a.expensive
    CACHE MISS
    2
    >>> a.reset_cache_expensive()
    >>> a.expensive
    CACHE MISS
    2
    """

    def __init__(self, ttl):
        # fake func
        super().__init__(self.__init__)
        self._real_func = None
        self._owner = None
        self._ttl = ttl

    def __call__(self, func):
        self.func = self.func_and_time
        self._real_func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        return self

    def __set_name__(self, owner, name):
        # add "_ttl" to attrname so it does not override the actual property/func
        super().__set_name__(owner, f'_{name}_ttl')
        self._owner = owner
        setattr(owner, f'reset_cache_{name}', lambda instance: self.clear_cache(instance))

    def clear_cache(self, instance):
        # expire cache
        try:
            del instance.__dict__[self.attrname]
        except KeyError:
            """ignore, not used yet"""

    def func_and_time(self, instance):
        return self._real_func(instance), time.time()

    def __get__(self, instance, owner=None):
        val, last_update = super().__get__(instance, owner=owner)
        if (time.time() - last_update) > self._ttl:
            self.clear_cache(instance)
            val, _ = super().__get__(instance, owner=owner)
        return val
