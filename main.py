import json
import argparse
from functools import reduce

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--path', type=str, default='-', help='Path to JSON file to generate models from')
    parser.add_argument('--pydantic', action='store_true', help='Generate pydantic models instead of dataclasses')
    parser.add_argument('-n', '--rootname', type=str, default='Root', help='Name of root class')
    parser.add_argument('-d', '--outdir', type=str, help='Directory to output to (default: stdout, formatted as one file)')
    parser.add_argument('--dry-run', dest='dry', action='store_true', help='Output to stdout, but show each file')

    args = parser.parse_args()

    return args


def read_stdin():
    line = input()
    while line != '':
        yield line
        try:
            line = input()
        except EOFError:
            line = ""


args = get_args()

if args.path == '-':
    data = '\n'.join(read_stdin())
else:
    with open(args.path) as fp:
        data = fp.read()

data = json.loads(data)

'''
class Root:
    spell: str

{
    "Root": {
        "spell": "str"
    }
}
'''

def debug(func):
    def _do(*args, **kwargs):
        print('->>', func.__name__, args, kwargs)
        retv = func(*args, **kwargs)
        print('<<-', func.__name__, retv)
        return retv
    return _do


def to_type_name(name: str) -> str:
    if name in ['str', 'int', 'float', 'bool']:
        return name

    if name[0].isupper():
        return name

    return name.replace('_', ' ').title().replace(' ', '')



def to_model_dict(name: str, obj, models: dict) -> None:
    if isinstance(obj, dict):
        type_name = to_type_name(name)
        models[type_name] = {}

        for k, v in obj.items():
            v_type = to_model_dict(k, v, models) or k

            models[type_name][k] = v_type

        return type_name

    if isinstance(obj, list):
        type_name = to_type_name(name)
        sub_type = type_name + 'Item'
        # models[type_name] = sub_type

        #TODO Merge elements of obj
        if len(obj) == 0:
            return 'Any'

        to_model_dict(sub_type, obj[0], models)

        return f'List[{sub_type}]'

    return to_type_name(type(obj).__name__)



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


class DataclassDecoration(ModelDecorator):
    def imports(self) -> str:
        yield 'from dataclasses import dataclass'
        yield ''
        yield ''

    def class_def(self, line: str) -> str:
        yield '@dataclass'
        yield line

    def property_def(self, line: str) -> str:
        yield line


class PydanticDecorator(ModelDecorator):
    def imports(self) -> str:
        yield 'from pydantic import BaseModel'
        yield ''
        yield ''

    def class_def(self, line: str) -> str:
        yield line[:-1] + '(BaseModel)' + ':'

    def property_def(self, line: str) -> str:
        yield line


class ModelPrinter:
    def print(self, model: dict, decorator: ModelDecorator) -> str:
        raise NotImplementedError

    def get_typing_imports(self, types):
        import_types = set(t[:t.find('[')] for t in types if '[' in t or t == 'Any')

        if len(import_types) == 0:
            return None

        return 'from typing import ' + ', '.join(import_types)


class SingleFilePrinter(ModelPrinter):
    def print(self, model: dict, decorator: ModelDecorator):
        types = reduce(lambda acc, curr: acc + curr, map(lambda prop: list(prop.values()), list(model.values())))
        if typing_imports := self.get_typing_imports(types):
            print(typing_imports)

        for line in decorator.imports():
            print(line)

        first = True
        for cls_name, props in model.items():
            if first:
                first = False
            else:
                print('')
                print('')

            for line in decorator.class_def(f'class {cls_name}:'):
                print(line)

            for prop_name, prop_type in props.items():
                for line in decorator.property_def(f'    {prop_name}: {prop_type}'):
                    print(line)

class MultiFilePrinter(ModelPrinter):
    def __init__(self, outdir: str) -> None:
        import os

        self._outdir = outdir
        os.makedirs(self._outdir, exist_ok=True)

    def _get_path(self, file_name: str) -> str:
        import os

        return os.path.join(self._outdir, file_name) + '.py'

    def print(self, model: dict, decorator: ModelDecorator):
        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}

        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            with open(self._get_path(fname), 'w') as fout:
                for line in self._get_lines(model, decorator, cls_name, props, cls2file):
                    fout.write(line + '\n')

    def _get_lines(self, model: dict, decorator: ModelDecorator, cls_name: str, props: dict, cls2file: dict):
            # Import typing requirements
            if typing_imports := self.get_typing_imports(props.values()):
                yield typing_imports

            # Import dependent types
            for prop_type in props.values():
                prop_type: str
                if '[' in prop_type:
                    stidx = prop_type.find('[')
                    edidx = prop_type.rfind(']')
                    prop_type = prop_type[stidx+1:edidx]
                if fname := cls2file.get(prop_type):
                    yield f'from .{fname} import {prop_type}'

            # Other imports
            for line in decorator.imports():
                yield line

            # Print class def
            for line in decorator.class_def(f'class {cls_name}:'):
                yield line

            # Print property defs
            for prop_name, prop_type in props.items():
                for line in decorator.property_def(f'    {prop_name}: {prop_type}'):
                    yield line


class MultiFileDryRunPrinter(MultiFilePrinter):
    def print(self, model: dict, decorator: ModelDecorator):
        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}

        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            print('##', self._get_path(fname))
            for line in self._get_lines(model, decorator, cls_name, props, cls2file):
                print(line)
            print()


all_models = dict()

to_model_dict(args.rootname, data, all_models)

decorator: ModelDecorator = DataclassDecoration() if not args.pydantic else PydanticDecorator()

printer: ModelPrinter
if args.outdir is not None:
    if args.dry:
        printer: ModelPrinter = MultiFileDryRunPrinter(args.outdir)
    else:
        printer: ModelPrinter = MultiFilePrinter(args.outdir)
else:
    printer: ModelPrinter = SingleFilePrinter()

printer.print(all_models, DataclassDecoration())
