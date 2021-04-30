import json
from typing import Optional
import typer
from dataclasses import dataclass


app = typer.Typer()


class TypeConverter:
    def to_type_name(self, name: str) -> str:
        raise NotImplementedError

    def get_unknown_type(self) -> str:
        raise NotImplementedError

    def list_type_format(self, element_name: str) -> str:
        raise NotImplementedError


def read_stdin():
    line = input()
    while line != '':
        yield line
        try:
            line = input()
        except EOFError:
            line = ""


def get_data(path: str):
    if path == '-':
        data = '\n'.join(read_stdin())
    else:
        with open(path) as fp:
            data = fp.read()

    data = json.loads(data)

    return data


def debug(func):
    def _do(*args, **kwargs):
        print('->>', func.__name__, args, kwargs)
        retv = func(*args, **kwargs)
        print('<<-', func.__name__, retv)
        return retv
    return _do


def elementize(word: str) -> str:
    if word.endswith('ies'):
        return word[:-3] + 'y'
    elif word.endswith('es'):
        return word[:-2] + 'e'
    elif word.endswith('s'):
        return word[:-1]
    else:
        return word + 'Item'


def to_model_dict(name: str, obj, models: dict, converter: TypeConverter) -> None:
    if isinstance(obj, dict):
        type_name = converter.to_type_name(name)
        models[type_name] = {}

        for k, v in obj.items():
            v_type = to_model_dict(k, v, models, converter) or k

            models[type_name][k] = v_type

        return type_name

    if isinstance(obj, list):
        type_name = converter.to_type_name(name)
        sub_type = elementize(type_name)
        # models[type_name] = sub_type

        #TODO Merge elements of obj
        if len(obj) == 0:
            return converter.get_unknown_type()

        sub_type = to_model_dict(sub_type, obj[0], models, converter)

        return converter.list_type_format(sub_type)

    return converter.to_type_name(type(obj).__name__)


class ModelDecorator:
    def imports(self) -> str:
        raise NotImplementedError

    def class_def(self, line: str) -> str:
        raise NotImplementedError

    def property_def(self, line: str) -> str:
        raise NotImplementedError


class NoDecoration(ModelDecorator):
    def imports(self) -> str:
        return []

    def class_def(self, line: str) -> str:
        yield line

    def property_def(self, line: str) -> str:
        yield line


class ModelPrinter:
    def __init__(self, decorator: ModelDecorator) -> None:
        self._decorator = decorator

    @property
    def decorator(self) -> ModelDecorator:
        return self._decorator

    def print(self, model: dict) -> str:
        raise NotImplementedError


def translate(printer: ModelPrinter, converter: TypeConverter, path: str, rootname: str):
    data = get_data(path)

    all_models = dict()
    to_model_dict(rootname, data, all_models, converter)

    printer.print(all_models)


@dataclass
class State:
    path: str
    rootname: str
    outdir: str

global_state: State


@app.callback()
def get_paths(path: str = '-', outdir: str = '-', rootname: str = 'Root'):
    global global_state

    global_state = State(path=path, rootname=rootname, outdir=outdir)


@app.command()
def python(pydantic: bool = False, dryrun: bool = False) -> None:
    from languages.python_generator import PyTypeConverter
    converter: TypeConverter = PyTypeConverter()

    decorator: ModelDecorator
    if not pydantic:
        from languages.python_generator import DataclassDecoration
        decorator = DataclassDecoration()
    else:
        from languages.python_generator import PydanticDecorator
        decorator = PydanticDecorator()

    printer: ModelPrinter
    if global_state.outdir == '-':
        from languages.python_generator import SingleFilePrinter
        printer: ModelPrinter = SingleFilePrinter(decorator)
    else:
        if dryrun:
            from languages.python_generator import MultiFileDryRunPrinter
            printer: ModelPrinter = MultiFileDryRunPrinter(decorator, global_state.outdir)
        else:
            from languages.python_generator import MultiFilePrinter
            printer: ModelPrinter = MultiFilePrinter(decorator, global_state.outdir)

    translate(printer, converter, global_state.path, global_state.rootname)


@app.command()
def typescript(dryrun: bool = False) -> None:
    from languages.typescript_generator import TSTypeConverter
    converter: TypeConverter = TSTypeConverter()

    decorator: ModelDecorator = NoDecoration()

    printer: ModelPrinter
    if global_state.outdir == '-':
        from languages.typescript_generator import SingleFilePrinter
        printer: ModelPrinter = SingleFilePrinter(decorator)
    else:
        if dryrun:
            from languages.typescript_generator import MultiFileDryRunPrinter
            printer: ModelPrinter = MultiFileDryRunPrinter(decorator, global_state.outdir)
        else:
            from languages.typescript_generator import MultiFilePrinter
            printer: ModelPrinter = MultiFilePrinter(decorator, global_state.outdir)

    translate(printer, converter, global_state.path, global_state.rootname)


@app.command()
def csharp(dryrun: bool = False) -> None:
    from languages.csharp_generator import CSTypeConverter
    converter: TypeConverter = CSTypeConverter()

    decorator: ModelDecorator = NoDecoration()

    printer: ModelPrinter
    if global_state.outdir == '-':
        from languages.csharp_generator import SingleFilePrinter
        printer: ModelPrinter = SingleFilePrinter(decorator)
    else:
        if dryrun:
            from languages.csharp_generator import MultiFileDryRunPrinter
            printer: ModelPrinter = MultiFileDryRunPrinter(decorator, global_state.outdir)
        else:
            from languages.csharp_generator import MultiFilePrinter
            printer: ModelPrinter = MultiFilePrinter(decorator, global_state.outdir)

    translate(printer, converter, global_state.path, global_state.rootname)


if __name__ == '__main__':
    app()
