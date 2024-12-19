import inspect
from typing import Any, Optional, Callable
import sys
import types


def get_class_from_method[T](method: Callable[[Any], Any]) -> type[T]:
    if inspect.isfunction(method) and '.' in method.__qualname__:
        class_name = method.__qualname__.split('.')[0]
    else:
        raise TypeError(f'{method} is not a method defined in a class')
    module = sys.modules[method.__module__]
    cls = getattr(module, class_name)
    return cls


def find_instance_of_class_in_attributes[T](instance: object, target_class: type[T]) -> Optional[T]:
    for attribute_name in dir(instance):
        attribute = getattr(instance, attribute_name)
        if (attribute_name.startswith('__') and attribute_name.endswith('__')
                or isinstance(attribute, (int, str, float, bool, list, dict, tuple))):
            continue
        if isinstance(attribute, target_class):
            return attribute
        else:
            result = find_instance_of_class_in_attributes(attribute, target_class)
            if result:
                return result
    return None


def bind_method_to_instance_of_origin_class_in_attributes[T, **P](
        method: Callable[[P], T], instance_with_attributes: object) -> Callable[[P], T]:
    print(method)
    cls = get_class_from_method(method)
    instance = find_instance_of_class_in_attributes(instance_with_attributes, cls)
    if not instance:
        raise AttributeError(f'The provided instance {instance_with_attributes} does not have an attribute '
                             f'of class {cls.__name__}')
    bound_command = types.MethodType(method, instance)
    return bound_command