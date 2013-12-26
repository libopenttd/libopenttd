class EnumHelper(object):
    is_flag = False
    __build = False
    __dict  = None
    __rdict = None
    __max   = None
    __min   = None

    @classmethod
    def _build(cls):
        if cls.__build:
            return
        cls.__build = True
        cls.__dict  = {}
        cls.__rdict = {}

        for item in dir(cls):
            if item.upper() != item:
                continue
            if item.startswith('_'):
                continue
            value = getattr(cls, item, None)
            cls.__dict[item] = value
            cls.__rdict[value] = item
        items = sorted(cls.__rdict.keys())
        if len(items) > 0:
            cls.__max = items[-1]
            cls.__min = items[0]

    @classmethod
    def is_valid(cls, value):
        cls._build()
        if cls.is_flag:
            return value >= 0 and value < cls.__max * 2
        else:
            return value in cls.__rdict

    @classmethod
    def get_name(cls, value):
        cls._build()
        return cls.__rdict.get(value, None)

    @classmethod
    def get_from_name(cls, name):
        cls._build()
        return cls.__dict.get(name, None)
