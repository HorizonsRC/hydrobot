from annalist import annalist
from inspect import getmembers, isfunction

flogger = annalist.FunctionLogger("Analyzing", "Nic Baby")


@flogger.annalize
def test_func(arg):
    print(arg)
    pass


if __name__ == "__main__":
    test_func("heyo")
