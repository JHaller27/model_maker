class TypeConverter:
    def to_type_name(self, name: str) -> str:
        raise NotImplementedError

    def get_unknown_type(self) -> str:
        raise NotImplementedError

    def list_type_format(self, element_name: str) -> str:
        raise NotImplementedError


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
