from printer_interfaces import ModelDecorator, ModelPrinter, TypeConverter


class TSTypeConverter(TypeConverter):
    primitive_map: dict = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
    }
    def to_type_name(self, name: str) -> str:
        if mapped_name := TSTypeConverter.primitive_map.get(name):
            return mapped_name

        if name[0].isupper():
            return name

        return name.replace('_', ' ').title().replace(' ', '')

    def get_unknown_type(self) -> str:
        return 'object'

    def list_type_format(self, element_name: str) -> str:
        return f'Array<{element_name}>'



class SingleFilePrinter(ModelPrinter):
    def print(self, model: dict):
        for line in self.decorator.imports():
            print(line)

        first = True
        for cls_name, props in model.items():
            if first:
                first = False
            else:
                print('')

            for line in self.decorator.class_def(f'export interface {cls_name} {{'):
                print(line)

            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    {prop_name}: {prop_type};'):
                    print(line)

            print('}')


class MultiFilePrinter(ModelPrinter):
    def __init__(self, decorator: ModelDecorator, outdir: str) -> None:
        import os

        super().__init__(decorator)

        self._outdir = outdir
        os.makedirs(self._outdir, exist_ok=True)

    def _get_path(self, file_name: str) -> str:
        import os

        return os.path.join(self._outdir, file_name) + '.ts'

    def print(self, model: dict):
        cls2file = {cn: cn[0].lower() + cn[1:] for cn in model}

        for cls_name, props in model.items():
            fname = cls2file[cls_name]
            with open(self._get_path(fname), 'w') as fout:
                for line in self._get_lines(cls_name, props, cls2file):
                    fout.write(line + '\n')

    def _get_lines(self, cls_name: str, props: dict, cls2file: dict):
            # Import dependent types
            has_imports = False
            for prop_type in props.values():
                prop_type: str
                if '<' in prop_type:
                    stidx = prop_type.find('<')
                    edidx = prop_type.rfind('>')
                    prop_type = prop_type[stidx+1:edidx]

                if fname := cls2file.get(prop_type):
                    has_imports = True
                    yield f"import {{ {prop_type} }} from './{fname}';"

            if has_imports:
                yield ''

            # Other imports
            for line in self.decorator.imports():
                yield line

            # Print class def
            for line in self.decorator.class_def(f'export interface {cls_name} {{'):
                yield line

            # Print property defs
            for prop_name, prop_type in props.items():
                for line in self.decorator.property_def(f'    {prop_name}: {prop_type};'):
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
