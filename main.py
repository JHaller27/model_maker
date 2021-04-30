import json
import argparse


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


def get_data(path):
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
    def __init__(self, decorator: ModelDecorator) -> None:
        self._decorator = decorator

    @property
    def decorator(self) -> ModelDecorator:
        return self._decorator

    def print(self, model: dict) -> str:
        raise NotImplementedError

    def get_typing_imports(self, types):
        import_types = set()
        for t in types:
            if t == 'Any':
                import_types.add(t)
            elif '[' in t:
                import_types.add(t[:t.find('[')])

        if len(import_types) == 0:
            return None

        return 'from typing import ' + ', '.join(import_types)


def generate_python() -> ModelPrinter:
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
            printer: ModelPrinter = MultiFileDryRunPrinter(decorator, args.outdir)
        else:
            from python_generator import MultiFilePrinter
            printer: ModelPrinter = MultiFilePrinter(decorator, args.outdir)
    else:
        from python_generator import SingleFilePrinter
        printer: ModelPrinter = SingleFilePrinter(decorator)

    return printer


def translate(printer: ModelPrinter, path: str, rootname: str):
    data = get_data(path)

    all_models = dict()
    to_model_dict(rootname, data, all_models)

    printer.print(all_models)


def main(args):
    # Select language
    if args.language == 'python':
        printer = generate_python()
    else:
        raise ValueError(f"language '{args.language}' is not supported")

    translate(printer, args.path, args.rootname)


if __name__ == '__main__':
    args = get_args()
    main(args)
