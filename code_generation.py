import json
import os

if os.name != 'nt':
    # auto-update the protos
    import subprocess

    # protoc must be installed and on path
    package_dir = os.path.join(os.getcwd(), 'yarrow')
    subprocess.call(f"protoc --python_out={package_dir} *.proto", shell=True, cwd=os.path.abspath('../prototypes/'))
    subprocess.call(f"sed -i -E 's/^import.*_pb2/from . &/' *.py", shell=True, cwd=package_dir)

if os.name == 'nt' and not os.path.exists('yarrow/api_pb2.py'):
    print('make sure to run protoc to generate python proto bindings, and fix package imports to be relative to yarrow')

components_dir = os.path.abspath("../prototypes/components")

generated_code = "from . import Component\n\n"
for file_name in os.listdir(components_dir):
    component_path = os.path.join(components_dir, file_name)
    with open(component_path, 'r') as component_schema_file:

        try:
            component_schema = json.load(component_schema_file)
        except json.JSONDecodeError as err:
            print("MALFORMED JSON FILE: ", file_name)
            raise err

        # remove dupes while keeping order
        signature_arguments = list(dict.fromkeys([
            *component_schema['arguments'].keys(),
            *component_schema['options'].keys(),
            '**kwargs']))

        # sort arguments with defaults to the end of the signature
        default_arguments = {
            True: [],
            False: []
        }

        # add default value to arguments
        for arg in list(dict.fromkeys([
            *component_schema['arguments'].keys(),
            *component_schema['options'].keys()])):

            if arg == '**kwargs':
                continue

            schema = component_schema['arguments'].get(arg, component_schema['options'].get(arg, {}))
            if 'default' in schema:
                default_arguments[True].append(arg + f'={schema["default"]}')
            else:
                default_arguments[False].append(arg)

        # create the function signature
        signature_string = ", ".join([*default_arguments[False], *default_arguments[True], '**kwargs'])

        # create the arguments to the Component constructor
        component_arguments = "{\n            "\
                              + ",\n            ".join([f"'{name}': Component.of({name})"
                                                      for name in component_schema['arguments']
                                                      if name != "**kwargs"]) \
                              + "\n        }"
        component_options = "{\n            " \
                            + ",\n            ".join([f"'{name}': {name}"
                                                      for name in component_schema['options']
                                                      if name != "**kwargs"]) \
                            + "\n        }"
        component_constraints = "None"

        # handle components with unknown number of arguments
        if "**kwargs" in component_schema['arguments']:
            component_arguments = f"{{**kwargs, **{component_arguments}}}"
        elif "**kwargs" in component_schema['options']:
            component_options = f"{{**kwargs, **{component_options}}}"
        else:
            component_constraints = "kwargs"

        # build the call to create a Component with the prior argument strings
        generated_code += f"""
def {component_schema['name']}({signature_string}):
    \"\"\"{component_schema.get("docstring", component_schema["name"] + " step")}\"\"\"
    return Component(
        "{component_schema['id']}",
        arguments={component_arguments},
        options={component_options},
        constraints={component_constraints})

"""
output_path = os.path.join(os.getcwd(), 'yarrow', 'components.py')
with open(output_path, 'w') as generated_file:
    generated_file.write(generated_code)
