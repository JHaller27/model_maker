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
    parser.add_argument('-l', '--language', type=str, default='python', help='Language to generate')

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


class ModelPrinter:
    def print(self, model: dict, decorator: ModelDecorator) -> str:
        raise NotImplementedError

    def get_typing_imports(self, types):
        import_types = set(t[:t.find('[')] for t in types if '[' in t or t == 'Any')

        if len(import_types) == 0:
            return None

        return 'from typing import ' + ', '.join(import_types)


def generate_python():
    all_models = dict()

    to_model_dict(args.rootname, data, all_models)

    decorator: ModelDecorator
    if not args.pydantic:
        from python_generator import DataclassDecoration
        decorator = DataclassDecoration()
    else:
        from python_generator import PydanticDecorator
        decorator = PydanticDecorator()

    printer: ModelPrinter
    if args.outdir is not None:
        if args.dry:
            from python_generator import MultiFileDryRunPrinter
            printer: ModelPrinter = MultiFileDryRunPrinter(args.outdir)
        else:
            from python_generator import MultiFilePrinter
            printer: ModelPrinter = MultiFilePrinter(args.outdir)
    else:
        from python_generator import SingleFilePrinter
        printer: ModelPrinter = SingleFilePrinter()

    printer.print(all_models, decorator)

if args.language == 'python':
    generate_python()
else:
    raise ValueError(f"language '{args.language}' is not supported")
