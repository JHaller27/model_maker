from printer_interfaces import ModelDecorator, ModelPrinter, TypeConverter

from functools import reduce


class PyTypeConverter(TypeConverter):
    def to_type_name(self, name: str) -> str:
        if name in ['str', 'int', 'float', 'bool']:
            return name

        if name[0].isupper():
            return name

        return name.replace('_', ' ').title().replace(' ', '')

    def get_unknown_type(self) -> str:
        return 'Any'

    def list_type_format(self, element_name: str) -> str:
        return f'List[{element_name}]'


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


class OptionalDecorator(ModelDecorator):
    def __init__(self, base: ModelDecorator) -> None:
        super().__init__()

        self._base = base

    def imports(self) -> str:
        yield 'from typing import Optional'
        for x in self._base.imports():
            yield x

    def class_def(self, line: str) -> str:
        for x in self._base.class_def(line):
            yield x

    def property_def(self, line: str) -> str:
        for x in self._base.property_def(line):
            parts = x.split(': ')
            yield f'{parts[0]}: Optional[{parts[1]}]'


class PythonPrinter(ModelPrinter):
    def get_typing_imports(self, types):
        import_types = set()
        import_types.add('Optional')
        for t in types:
            if t == 'Any':
                import_types.add(t)
            elif '[' in t:
                import_types.add(t[:t.find('[')])

        if len(import_types) == 0:
            return None

        return 'from typing import ' + ', '.join(import_types)

    def print(self, model: dict) -> str:
        super().__init__(model)


class SingleFilePrinter(PythonPrinter):
    def print(self, model: dict):
        types = reduce(lambda acc, curr: acc + curr, map(lambda prop: list(prop.values()), list(model.values())))
        if typing_imports := self.get_typing_imports(types):
            print(typing_imports)

        for line in self.decorator.imports():
            print(line)

        first = True
        for cls_name, props in model.items():
            if first:
                first = False
            else:
                print('')
                print('')

            for line in self.decorator.class_def(f'class {cls_name}:'):
                print(line)

            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    {prop_name}: Optional[{prop_type}]'):
                    print(line)


class MultiFilePrinter(PythonPrinter):
    def __init__(self, decorator: ModelDecorator, outdir: str) -> None:
        super().__init__(decorator)

        self._outdir = outdir

    def _get_path(self, file_name: str) -> str:
        import os

        return os.path.join(self._outdir, file_name) + '.py'

    def print(self, model: dict):
        import os

        os.makedirs(self._outdir, exist_ok=True)

        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}

        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            with open(self._get_path(fname), 'w') as fout:
                for line in self._get_lines(cls_name, props, cls2file):
                    fout.write(line + '\n')

    def _get_lines(self, cls_name: str, props: dict, cls2file: dict):
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
            for line in self.decorator.imports():
                yield line

            # Print class def
            for line in self.decorator.class_def(f'class {cls_name}:'):
                yield line

            # Print property defs
            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    {prop_name}: Optional[{prop_type}]'):
                    yield line


class MultiFileDryRunPrinter(MultiFilePrinter):
    def print(self, model: dict):
        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}

        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            print('##', self._get_path(fname))
            for line in self._get_lines(cls_name, props, cls2file):
                print(line)
            print()
