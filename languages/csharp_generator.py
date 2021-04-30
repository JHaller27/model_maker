from printer_interfaces import ModelDecorator, ModelPrinter, TypeConverter
from functools import reduce


class CSTypeConverter(TypeConverter):
    primitive_map: dict = {
        'str': 'string',
        'int': 'int',
        'float': 'float',
        'bool': 'bool',
    }
    def to_type_name(self, name: str) -> str:
        if mapped_name := CSTypeConverter.primitive_map.get(name):
            return mapped_name

        if name[0].isupper():
            return name

        return name.replace('_', ' ').title().replace(' ', '')

    def get_unknown_type(self) -> str:
        return 'object'

    def list_type_format(self, element_name: str) -> str:
        return f'IEnumerable<{element_name}>'


class CSharpPrinter(ModelPrinter):
    def get_typing_imports(self, types):
        import_types = set()
        for t in types:
            if 'IEnumerable' in t:
                import_types.add('System.Collections.Generic')

        if len(import_types) == 0:
            return None

        return ''.join(f'using {it};\n' for it in import_types)

    def print(self, model: dict) -> str:
        super().__init__(model)


class SingleFilePrinter(CSharpPrinter):
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

            for line in self.decorator.class_def(f'public class {cls_name}'):
                print(line)
            print('}')

            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    public {prop_type} {prop_name} {{ get; set; }}'):
                    print(line)
            print('}')


class MultiFilePrinter(CSharpPrinter):
    def __init__(self, decorator: ModelDecorator, outdir: str) -> None:
        import os

        super().__init__(decorator)

        self._outdir = outdir
        os.makedirs(self._outdir, exist_ok=True)

    def _get_path(self, file_name: str) -> str:
        import os

        return os.path.join(self._outdir, file_name) + '.cs'

    def print(self, model: dict):
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

            # Other imports
            for line in self.decorator.imports():
                yield line

            # Print class def
            for line in self.decorator.class_def(f'public class {cls_name}'):
                yield line
            yield '{'

            # Print property defs
            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    public {prop_type} {prop_name} {{ get; set; }}'):
                    yield line
            yield '}'


class MultiFileDryRunPrinter(MultiFilePrinter):
    def print(self, model: dict):
        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}
        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            print('##', self._get_path(fname))
            for line in self._get_lines(cls_name, props, cls2file):
                print(line)
            print()
